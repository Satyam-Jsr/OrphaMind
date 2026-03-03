import { useState, useRef, useEffect } from 'react'
import { api } from '../api.js'
import { Card, CardTitle, Input, Btn, Badge, Spinner } from './ui.jsx'

const prevalenceStr = (p) => typeof p === 'object' ? (p?.class || '') : (p || '')
const prevalenceColor = (p) => {
  const s = prevalenceStr(p)
  if (!s) return 'gray'
  if (s.includes('1/') && parseInt(s.split('/')[1]) > 1000000) return 'red'
  if (s.includes('1/') && parseInt(s.split('/')[1]) > 100000) return 'orange'
  return 'blue'
}

const SL = ({ label }) => (
  <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em', color: '#2a4060', marginBottom: 8, marginTop: 14 }}>
    {label}
  </div>
)

function DiseaseDetail({ disease, onClose }) {
  const [showAllHpo, setShowAllHpo] = useState(false)
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])
  if (!disease) return null
  const inheritance = Array.isArray(disease.inheritance)
    ? disease.inheritance.join(', ')
    : (disease.inheritance || '')
  const ageOnset = Array.isArray(disease.age_of_onset)
    ? disease.age_of_onset.join(', ')
    : (disease.age_of_onset || '')

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.75)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#08111e', border: '1px solid #1c2d44', borderRadius: 16,
        padding: 28, maxWidth: 640, width: '100%', maxHeight: '85vh', overflowY: 'auto',
        animation: 'fadeIn .2s ease',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18, color: '#d4e2f5', marginBottom: 6, lineHeight: 1.3 }}>
              {disease.name}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {disease.orpha_id && <Badge color="blue">ORPHA:{disease.orpha_id}</Badge>}
              {disease.omim_id && <Badge color="purple">OMIM:{disease.omim_id}</Badge>}
              {disease.type && <Badge color="gray">{disease.type}</Badge>}
              {disease.prevalence && prevalenceStr(disease.prevalence) && (
                <Badge color={prevalenceColor(disease.prevalence)}>Prev: {prevalenceStr(disease.prevalence)}</Badge>
              )}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6a87a8', fontSize: 22, cursor: 'pointer', marginLeft: 12 }}>×</button>
        </div>

        {/* Synonyms */}
        {disease.synonyms?.length > 0 && (
          <>
            <SL label="Also Known As" />
            <div style={{ fontSize: 12, color: '#4a7aaa', lineHeight: 1.6, marginBottom: 2 }}>
              {disease.synonyms.join(' · ')}
            </div>
          </>
        )}

        {/* Quick facts row */}
        {(inheritance || ageOnset) && (
          <div style={{ display: 'flex', gap: 20, marginTop: 14, flexWrap: 'wrap' }}>
            {inheritance && (
              <div style={{ fontSize: 12, color: '#6a87a8' }}>
                <strong style={{ color: '#60a5fa' }}>Inheritance:</strong> {inheritance}
              </div>
            )}
            {ageOnset && (
              <div style={{ fontSize: 12, color: '#6a87a8' }}>
                <strong style={{ color: '#60a5fa' }}>Age of Onset:</strong> {ageOnset}
              </div>
            )}
          </div>
        )}

        {/* Genes */}
        {disease.genes?.length > 0 && (
          <>
            <SL label="Associated Genes" />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {disease.genes.map((g, i) => (
                <span key={i} style={{
                  background: '#0d2137', border: '1px solid #1a3a5c', borderRadius: 6,
                  padding: '3px 8px', fontSize: 12, color: '#93c5fd',
                  fontFamily: 'monospace',
                }}>
                  {g.symbol || g}
                  {g.name && g.symbol && <span style={{ color: '#3d6494', marginLeft: 4 }}>— {g.name}</span>}
                </span>
              ))}
            </div>
          </>
        )}

        {/* HPO terms */}
        {disease.hpo_terms?.length > 0 && (
          <>
            <SL label={`HPO Phenotypes (${disease.hpo_terms.length})`} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {(showAllHpo ? disease.hpo_terms : disease.hpo_terms.slice(0, 12)).map((h, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                  <span style={{ color: '#a8c8e8' }}>{h.term || h}</span>
                  {h.frequency && (
                    <span style={{ color: '#2a4060', fontSize: 11, marginLeft: 8, whiteSpace: 'nowrap' }}>{h.frequency}</span>
                  )}
                </div>
              ))}
              {disease.hpo_terms.length > 12 && (
                <button
                  onClick={() => setShowAllHpo(v => !v)}
                  style={{
                    marginTop: 6, background: 'none', border: '1px solid #1c3050',
                    borderRadius: 6, padding: '4px 10px', fontSize: 11,
                    color: '#3b82f6', cursor: 'pointer', alignSelf: 'flex-start',
                  }}
                >
                  {showAllHpo
                    ? '▲ Show less'
                    : `▼ Show all ${disease.hpo_terms.length} phenotypes`}
                </button>
              )}
            </div>
          </>
        )}

        {/* Symptoms (fallback if no HPO terms) */}
        {disease.symptoms?.length > 0 && !disease.hpo_terms?.length && (
          <>
            <SL label="Symptoms" />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {disease.symptoms.map((s, i) => (
                <span key={i} className="sym-pill">{s}</span>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function SearchTab() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const debounceRef = useRef()

  const doSearch = async (q) => {
    if (!q.trim()) { setResults([]); return }
    setLoading(true); setError(null)
    try {
      const r = await api.searchDiseases(q.trim())
      setResults(r.results || [])
    } catch { setError('Search failed') }
    setLoading(false)
  }

  const handleChange = (val) => {
    setQuery(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => doSearch(val), 500)
  }

  const openDisease = async (d) => {
    const id = d.orpha_id || d.orphanet_id || d.id
    if (!id) { setSelected(d); return }
    setDetailLoading(true)
    try {
      const detail = await api.getDisease(id)
      setSelected(detail)
    } catch { setSelected(d) }
    setDetailLoading(false)
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card style={{ marginBottom: 20 }}>
        <CardTitle>Search Rare Diseases (11,456 in Index)</CardTitle>
        <Input
          value={query}
          onChange={handleChange}
          placeholder="Search by name, gene, symptom, OMIM / ORPHA ID…"
        />
      </Card>

      {detailLoading && (
        <div style={{ position: 'fixed', inset: 0, background: '#000a', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999 }}>
          <Spinner size={48} />
        </div>
      )}

      {selected && <DiseaseDetail disease={selected} onClose={() => setSelected(null)} />}

      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner size={36} />
        </div>
      )}

      {error && !loading && (
        <div style={{ background: '#1a0404', border: '1px solid #380e0e', borderRadius: 10, padding: '12px 16px', color: '#ef4444', fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {results.length > 0 && !loading && (
        <Card>
          <CardTitle>{results.length} Results</CardTitle>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {results.map((d, i) => (
              <div
                key={i}
                onClick={() => openDisease(d)}
                className="case-row"
                style={{ minWidth: 180, flex: '1 1 180px', marginBottom: 0 }}
              >
                <div style={{ color: '#d4e2f5', fontWeight: 600, fontSize: 13, marginBottom: 5, lineHeight: 1.3 }}>
                  {d.name}
                </div>
                {d.synonyms?.length > 0 && (
                  <div style={{ fontSize: 11, color: '#3d6494', marginBottom: 5, lineHeight: 1.4 }}>
                    Also: {d.synonyms.slice(0, 3).join(' · ')}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                  {d.orpha_id && <Badge color="blue">ORPHA:{d.orpha_id}</Badge>}
                  {d.prevalence && prevalenceStr(d.prevalence) && <Badge color={prevalenceColor(d.prevalence)}>{prevalenceStr(d.prevalence)}</Badge>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {!loading && !results.length && query && (
        <div style={{ textAlign: 'center', color: '#2a4060', padding: 40 }}>No diseases found for "{query}"</div>
      )}

      {!query && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '56px 32px' }}>
          <div style={{ fontSize: 40, opacity: .2 }}>🔍</div>
          <div style={{ color: '#1c2d44', fontSize: 13, maxWidth: 320, textAlign: 'center' }}>
            Try "CIPA", "Wilson", "SMA", "ATP7B", "HSAN", or any name, acronym, gene, or symptom.
          </div>
        </div>
      )}
    </div>
  )
}
