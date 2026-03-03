import { useState } from 'react'
import { Card, CardTitle, Badge } from './ui.jsx'

function urgencyColor(u) {
  if (!u) return 'gray'
  const l = u.toLowerCase()
  if (l.includes('emergency')) return 'red'
  if (l.includes('urgent')) return 'orange'
  return 'green'
}

function ConfBar({ pct }) {
  const color = pct >= 70 ? '#34d399' : pct >= 40 ? '#f97316' : '#ef4444'
  return (
    <div style={{ height: 5, background: '#0d1829', borderRadius: 99, overflow: 'hidden', margin: '8px 0 4px' }}>
      <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 99, transition: 'width 1s cubic-bezier(.4,0,.2,1)' }} />
    </div>
  )
}

function DiseaseCard({ d, rank }) {
  const [expanded, setExpanded] = useState(false)
  // Support both decimal (0-1) and integer (0-100) confidence values
  const pct = d.confidence > 1 ? Math.round(d.confidence) : Math.round((d.confidence || 0) * 100)
  const hasWarning = d.hallucination_warning || d.warning
  const reasoning = d.reasoning || ''

  return (
    <div style={{
      background: '#060d18',
      border: '1px solid #1c2d44',
      borderLeft: `3px solid ${pct >= 70 ? '#34d399' : pct >= 40 ? '#f97316' : '#475569'}`,
      borderRadius: 10, padding: '14px 16px', marginBottom: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
            <span style={{ background: '#0d1829', color: '#334d68', fontSize: 10, fontWeight: 800, padding: '1px 7px', borderRadius: 20 }}>#{rank}</span>
            <span style={{ color: '#d4e2f5', fontWeight: 700, fontSize: 14 }}>{d.disease || d.name}</span>
            {d.verified_in_orphanet && <Badge color="green">✓ Orphanet</Badge>}
            {hasWarning && <Badge color="orange">⚠ Low evidence</Badge>}
            {d.inheritance && d.inheritance !== 'unknown' && <Badge color="purple">{d.inheritance}</Badge>}
          </div>
          {(d.orpha_id || d.orphanet_id) && (
            <div style={{ fontSize: 10, color: '#2a4060', marginTop: 3 }}>
              ORPHA:{d.orpha_id || d.orphanet_id}{d.omim_id && ` · OMIM:${d.omim_id}`}
            </div>
          )}
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 22, fontWeight: 800, lineHeight: 1, color: pct >= 70 ? '#34d399' : pct >= 40 ? '#f97316' : '#ef4444' }}>{pct}%</div>
          <div style={{ fontSize: 9, color: '#2a4060', textTransform: 'uppercase', letterSpacing: '.06em' }}>confidence</div>
        </div>
      </div>

      <ConfBar pct={pct} />

      {reasoning && (
        <div style={{ marginTop: 8, color: '#6a87a8', fontSize: 12, lineHeight: 1.7 }}>
          {expanded ? reasoning : reasoning.slice(0, 240) + (reasoning.length > 240 ? '…' : '')}
          {reasoning.length > 240 && (
            <button type="button" onClick={() => setExpanded(v => !v)} style={{
              background: 'none', border: 'none', color: '#3b82f6',
              cursor: 'pointer', fontSize: 11, fontWeight: 600, padding: '0 4px',
            }}>{expanded ? '▲ less' : '▼ more'}</button>
          )}
        </div>
      )}

      {expanded && (
        <div style={{ display: 'flex', gap: 12, marginTop: 10, flexWrap: 'wrap' }}>
          {d.supporting_features?.length > 0 && (
            <div style={{ flex: 1, minWidth: 140 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#34d399', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '.06em' }}>Supporting</div>
              {d.supporting_features.map((f, i) => <div key={i} style={{ fontSize: 11, color: '#6a87a8', lineHeight: 1.65 }}>✓ {f}</div>)}
            </div>
          )}
          {d.against_evidence?.length > 0 && (
            <div style={{ flex: 1, minWidth: 140 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#ef4444', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '.06em' }}>Against</div>
              {d.against_evidence.map((f, i) => <div key={i} style={{ fontSize: 11, color: '#6a87a8', lineHeight: 1.65 }}>✗ {f}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ResultsPanel({ result }) {
  const [refsOpen, setRefsOpen] = useState(false)
  if (!result) return null

  const diagnoses = result.differential_diagnosis || result.diagnoses || []
  const refs = result.literature_references || result.references || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Report header */}
      <Card glow>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#dce8f6', marginBottom: 8, letterSpacing: '-.02em' }}>Diagnostic Report</div>
            <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', alignItems: 'center' }}>
              {result.urgency && <Badge color={urgencyColor(result.urgency)}>{result.urgency}</Badge>}
              {result.llm_backend && <Badge color="purple">{result.llm_backend.toUpperCase()}</Badge>}
              {result.processing_time_ms && <Badge color="gray">⏱ {(result.processing_time_ms / 1000).toFixed(1)}s</Badge>}
              {diagnoses.length > 0 && <Badge color="blue">{diagnoses.length} candidates</Badge>}
            </div>
          </div>
          {result.case_id && (
            <div style={{ fontSize: 10, color: '#2a4060' }}>Case <span style={{ color: '#60a5fa', fontFamily: 'monospace', fontWeight: 700 }}>#{result.case_id}</span></div>
          )}
        </div>
        {result.summary && (
          <div style={{ marginTop: 12, padding: '10px 14px', background: '#08111e', borderRadius: 8, border: '1px solid #1c2d44', color: '#6a87a8', fontSize: 12, lineHeight: 1.72 }}>
            {result.summary}
          </div>
        )}
      </Card>

      {/* Differential */}
      {diagnoses.length > 0 && (
        <Card>
          <CardTitle>Differential Diagnosis ({diagnoses.length})</CardTitle>
          {diagnoses.map((d, i) => <DiseaseCard key={i} d={d} rank={i + 1} />)}
        </Card>
      )}

      {/* Workup */}
      {result.recommended_tests?.length > 0 && (
        <Card>
          <CardTitle>Recommended Workup</CardTitle>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {result.recommended_tests.map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '7px 0',
                borderBottom: i < result.recommended_tests.length - 1 ? '1px solid #0d1829' : 'none' }}>
                <span style={{ background: '#08111e', color: '#3b82f6', fontSize: 10, fontWeight: 800,
                  padding: '2px 7px', borderRadius: 4, flexShrink: 0 }}>{i + 1}</span>
                <span style={{ color: '#6a87a8', fontSize: 12, lineHeight: 1.65 }}>{t}</span>
              </div>
            ))}
          </div>
          {result.urgency_reason && (
            <div style={{ marginTop: 10, padding: '8px 12px', background: '#060e18', borderRadius: 7, fontSize: 11, color: '#60a5fa', border: '1px solid #0e2040' }}>
              💡 {result.urgency_reason}
            </div>
          )}
        </Card>
      )}

      {/* Literature References — refs from RAG have {content, source, type, score} */}
      {refs.length > 0 && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <CardTitle style={{ marginBottom: 0 }}>Literature Evidence ({refs.length})</CardTitle>
            <button
              type="button"
              onClick={() => setRefsOpen(v => !v)}
              style={{
                background: refsOpen ? '#08111e' : 'transparent', border: '1px solid #1c2d44',
                borderRadius: 6, color: '#3b82f6', fontSize: 11, fontWeight: 600,
                cursor: 'pointer', padding: '4px 12px', transition: 'background .15s',
              }}
            >
              {refsOpen ? '▲ Collapse' : '▼ Expand'}
            </button>
          </div>

          {refsOpen && (
            <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {refs.map((r, i) => {
                const heading = typeof r === 'string' ? r : (r.source || r.title || `Reference ${i + 1}`)
                const excerpt = typeof r === 'object' ? (r.content || r.excerpt || '') : ''
                const docType = typeof r === 'object' ? r.type : null
                return (
                  <div key={i} style={{ background: '#060d18', border: '1px solid #1c2d44', borderRadius: 8, padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                      <span style={{ background: '#08111e', color: '#60a5fa', fontSize: 10, fontWeight: 800,
                        padding: '2px 7px', borderRadius: 4, flexShrink: 0, marginTop: 1 }}>[{i + 1}]</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ color: '#93c5fd', fontSize: 12, fontWeight: 600 }}>
                          {heading}
                          {docType && <span style={{ marginLeft: 8, fontSize: 10, color: '#2a4060', textTransform: 'uppercase', fontWeight: 400 }}>{docType}</span>}
                        </div>
                        {excerpt && (
                          <div style={{ color: '#334d68', fontSize: 11, lineHeight: 1.65, marginTop: 5 }}>
                            {excerpt.slice(0, 220)}{excerpt.length > 220 ? '…' : ''}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      )}

      {/* Disclaimer */}
      <div style={{ border: '1px dashed #1c2d44', borderRadius: 10, padding: '10px 16px', color: '#2a4060', fontSize: 11, lineHeight: 1.6 }}>
        ⚠ <strong style={{ color: '#334d68' }}>Research Tool Only.</strong> OrphaMind is for educational and research purposes.
        Output must NOT be used for clinical decision-making without evaluation by a qualified medical professional.
      </div>

    </div>
  )
}


