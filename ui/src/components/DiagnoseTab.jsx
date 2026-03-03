import { useState, useRef, useCallback, useEffect } from 'react'
import { api } from '../api.js'
import { Card, CardTitle, Btn, Textarea, Input, Badge, Spinner, Divider } from './ui.jsx'
import ResultsPanel from './ResultsPanel.jsx'
import LabPanel from './LabPanel.jsx'

const STEPS = [
  { id: 'extract',  label: 'Extracting clinical features…' },
  { id: 'search',   label: 'Searching 11,456 rare diseases…' },
  { id: 'lit',      label: 'Querying literature (87,848 docs)…' },
  { id: 'diagnose', label: 'Generating diagnostic report…' },
]

const EXAMPLES = [
  { label: 'DMD', note: '8-year-old boy with progressive muscle weakness, difficulty climbing stairs, positive Gowers sign, CK 12000 IU/L, calf pseudohypertrophy.' },
  { label: 'Wilson', note: '22-year-old with hepatic dysfunction, Kayser-Fleischer rings, neuropsychiatric symptoms, low ceruloplasmin 8 mg/dL, elevated 24h urine copper.' },
  { label: 'Gaucher', note: 'Adult with hepatosplenomegaly, bone pain, thrombocytopenia, fatigue. Bone marrow shows lipid-laden macrophages.' },
  { label: 'CF', note: '6-year-old with recurrent pulmonary infections, failure to thrive, steatorrhea, sweat chloride 78 mEq/L, positive newborn screen.' },
  { label: 'Huntington', note: '45-year-old with chorea, cognitive decline, psychiatric symptoms, positive family history (autosomal dominant), CAG repeat expansion.' },
  { label: 'MPS', note: 'Child with coarse facial features, gibbus deformity, corneal clouding, recurrent otitis media, short stature, urine MPS elevated.' },
]

const SYMPTOMS = [
  'Muscle weakness','Seizures','Intellectual disability','Developmental delay','Short stature',
  'Hepatomegaly','Splenomegaly','Cardiomegaly','Renal failure','Hearing loss',
  'Vision loss','Cataracts','Corneal clouding','Nystagmus','Ataxia',
  'Tremor','Chorea','Dystonia','Spasticity','Hypotonia',
  'Hypertonia','Failure to thrive','Fatigue','Recurrent infections','Coarse facial features',
  'Macroglossia','Organomegaly','Jaundice','Ascites','Portal hypertension',
  'Cardiomyopathy','Arrhythmia','Pulmonary hypertension','Anemia','Thrombocytopenia',
  'Leukopenia','Hemolysis','Bone pain','Fractures','Osteoporosis',
  'Skin hyperpigmentation','Rash','Alopecia','Photosensitivity','Peripheral neuropathy',
  'Autonomic dysfunction','Psychiatric symptoms','Behavioral changes','Movement disorder','Eye abnormalities',
  'Facial dysmorphism','Webbed neck','Pectus excavatum','Scoliosis','Contractures',
  'Episodic vomiting','Diarrhea','Steatorrhea','Hypoglycemia','Hyperammonemia',
]

export default function DiagnoseTab({ loadCase }) {
  const [note, setNote] = useState('')
  const [patientId, setPatientId] = useState('')
  const [topK, setTopK] = useState(5)
  const [includeLit, setIncludeLit] = useState(true)
  const [symptomOpen, setSymptomOpen] = useState(false)
  const [selectedSymptoms, setSelectedSymptoms] = useState([])
  const [symptomFilter, setSymptomFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadStep, setLoadStep] = useState(0)   // 0-3 while loading
  const [validating, setValidating] = useState(false)
  const [validateMsg, setValidateMsg] = useState(null)
  const [result, setLocalResult] = useState(null)
  const [error, setError] = useState(null)
  const [ocrLoading, setOcrLoading] = useState(false)
  const [ocrMode, setOcrMode] = useState('typed')
  const [ocrResult, setOcrResult] = useState(null)
  const fileRef    = useRef()
  const debounceRef = useRef()
  const stepTimer  = useRef()

  // Auto-advance loading step indicator
  useEffect(() => {
    if (loading) {
      setLoadStep(0)
      const delays = [0, 2200, 5000, 8500]
      stepTimer.current = delays.map((d, i) =>
        setTimeout(() => setLoadStep(i), d)
      )
    } else {
      stepTimer.current?.forEach?.(t => clearTimeout(t))
    }
    return () => stepTimer.current?.forEach?.(t => clearTimeout(t))
  }, [loading])

  // Load a history case without unmounting the component
  useEffect(() => {
    if (!loadCase) return
    setNote(loadCase.note || '')
    setLocalResult(loadCase.result || null)
    setError(null)
    setValidateMsg(null)
    setOcrResult(null)
    setSelectedSymptoms([])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadCase?.loadId])

  const handleNoteChange = useCallback((val) => {
    setNote(val)
    setValidateMsg(null)
    clearTimeout(debounceRef.current)
    if (val.length > 40) {
      debounceRef.current = setTimeout(async () => {
        setValidating(true)
        try {
          const r = await api.validateNote(val)
          setValidateMsg({ ok: r.valid, text: r.message || (r.valid ? 'Note looks good' : 'Invalid input') })
        } catch {}
        setValidating(false)
      }, 900)
    }
  }, [])

  const handleOcr = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setOcrLoading(true)
    setOcrResult(null)
    try {
      const r = await api.ocrNote(file, ocrMode)
      if (r.text) {
        setNote(prev => prev ? prev + '\n' + r.text : r.text)
        setOcrResult({ chars: r.char_count, labs: r.detected_labs?.length || 0 })
      } else if (r.detail) {
        setError('OCR: ' + r.detail)
      }
    } catch { setError('OCR failed — check server is running') }
    setOcrLoading(false)
    e.target.value = ''
  }

  const toggleSymptom = (s) => {
    setSelectedSymptoms(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])
  }

  const buildNote = () => {
    if (!selectedSymptoms.length) return
    const added = 'Patient presents with: ' + selectedSymptoms.join(', ') + '.'
    setNote(prev => prev ? prev + '\n' + added : added)
    setSymptomOpen(false)
  }

  const handleDiagnose = async () => {
    if (!note.trim()) return
    setLoading(true)
    setError(null)
    setLocalResult(null)
    try {
      const r = await api.diagnose({
        clinical_note: note,
        patient_id: patientId || undefined,
        top_k_diseases: topK,
        include_literature: includeLit,
        save_to_history: true,
      })
      setLocalResult(r)
      if (typeof onDiagnosed === 'function') onDiagnosed(r)
    } catch (e) {
      setError(e?.message || 'Request failed')
    }
    setLoading(false)
  }

  const filteredSymptoms = SYMPTOMS.filter(s =>
    s.toLowerCase().includes(symptomFilter.toLowerCase())
  )

  return (
    <div className="diagnose-grid">

      {/* LEFT — Input */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Card>
          <CardTitle>Clinical Note</CardTitle>

          <Textarea
            rows={9}
            value={note}
            onChange={handleNoteChange}
            placeholder="Paste or type clinical findings — symptoms, signs, labs, age, demographics…"
          />

          {/* Validation chip */}
          {(validating || validateMsg) && (
            <div style={{ marginTop: 8, fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
              {validating
                ? <><Spinner size={12} /> <span style={{ color: '#8899aa' }}>Validating…</span></>
                : validateMsg && (
                  <span style={{ color: validateMsg.ok ? '#34d399' : '#f87171' }}>
                    {validateMsg.ok ? '✓' : '✗'} {validateMsg.text}
                  </span>
                )
              }
            </div>
          )}

          <div style={{ display: 'flex', gap: 7, marginTop: 12, flexWrap: 'wrap' }}>
            {EXAMPLES.map(ex => (
              <button key={ex.label} className="ex-chip" onClick={() => setNote(ex.note)}>
                {ex.label}
              </button>
            ))}
          </div>
        </Card>

        {/* OCR */}
        <Card>
          <CardTitle>Upload Document / Image</CardTitle>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <input type="file" ref={fileRef} accept="image/*,.pdf" onChange={handleOcr} style={{ display: 'none' }} />
            <Btn variant="secondary" onClick={() => fileRef.current.click()} disabled={ocrLoading} small style={{ flex: 1 }}>
              {ocrLoading ? <><Spinner size={14} /> Extracting…</> : '\uD83D\uDCC4 Extract Text via OCR'}
            </Btn>
            {/* Typed / Handwritten toggle */}
            <div style={{ display: 'flex', gap: 0, borderRadius: 8, overflow: 'hidden', border: '1px solid #1e2d45' }}>
              {['typed', 'handwritten'].map(mode => (
                <button
                  key={mode}
                  onClick={() => setOcrMode(mode)}
                  style={{
                    padding: '5px 11px', border: 'none', cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                    background: ocrMode === mode ? '#1e3a6e' : '#080b12',
                    color: ocrMode === mode ? '#60a5fa' : '#445566',
                    transition: 'all .2s',
                  }}
                >
                  {mode === 'typed' ? '\uD83D\uDDA8 Typed' : '\u270D Handwritten'}
                </button>
              ))}
            </div>
          </div>
          {ocrResult && (
            <div style={{ marginTop: 8, fontSize: 11, color: '#34d399' }}>
              \u2713 Extracted {ocrResult.chars} chars
              {ocrResult.labs > 0 && ` · ${ocrResult.labs} lab value${ocrResult.labs > 1 ? 's' : ''} detected`}
               — text added to note above
            </div>
          )}
        </Card>

        {/* Options */}
        <Card>
          <CardTitle>Options</CardTitle>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
            <label style={{ color: '#8899aa', fontSize: 12 }}>
              Patient ID
              <Input value={patientId} onChange={setPatientId} placeholder="optional" style={{ marginTop: 4, width: 130 }} />
            </label>
            <label style={{ color: '#8899aa', fontSize: 12 }}>
              Top K
              <select value={topK} onChange={e => setTopK(+e.target.value)} style={{
                display: 'block', marginTop: 4, background: '#080b12', border: '1px solid #1e2d45',
                borderRadius: 8, color: '#e8edf5', fontSize: 13, padding: '7px 10px', cursor: 'pointer',
              }}>
                {[3,5,8,10].map(k => <option key={k}>{k}</option>)}
              </select>
            </label>
            <label style={{ color: '#8899aa', fontSize: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
              Literature RAG
              <div
                onClick={() => setIncludeLit(v => !v)}
                style={{
                  width: 44, height: 24, borderRadius: 999,
                  background: includeLit ? '#3b82f6' : '#1e2d45',
                  cursor: 'pointer', position: 'relative', transition: 'background .25s',
                }}
              >
                <div style={{
                  position: 'absolute', top: 3, left: includeLit ? 23 : 3,
                  width: 18, height: 18, borderRadius: '50%',
                  background: '#fff', transition: 'left .25s',
                }} />
              </div>
            </label>
          </div>
        </Card>

        {/* Symptom builder */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <CardTitle style={{ marginBottom: 0 }}>Symptom Builder</CardTitle>
            <button onClick={() => setSymptomOpen(v => !v)} style={{
              background: 'none', border: '1px solid #1e2d45', borderRadius: 6,
              color: '#8899aa', fontSize: 11, cursor: 'pointer', padding: '3px 8px',
            }}>
              {symptomOpen ? '▲ hide' : '▼ show'}
            </button>
          </div>

          {selectedSymptoms.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
              {selectedSymptoms.map(s => (
                <button key={s} className="sym-pill selected" onClick={() => toggleSymptom(s)}>
                  {s} ×
                </button>
              ))}
            </div>
          )}

          {symptomOpen && (
            <div style={{ marginTop: 14 }}>
              <Input value={symptomFilter} onChange={setSymptomFilter} placeholder="Filter symptoms…" style={{ marginBottom: 10 }} />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 200, overflowY: 'auto' }}>
                {filteredSymptoms.map(s => (
                  <button
                    key={s}
                    className={`sym-pill${selectedSymptoms.includes(s) ? ' selected' : ''}`}
                    onClick={() => toggleSymptom(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
              {selectedSymptoms.length > 0 && (
                <Btn variant="secondary" onClick={buildNote} style={{ marginTop: 10 }} small>
                  + Add {selectedSymptoms.length} symptom{selectedSymptoms.length > 1 ? 's' : ''} to note
                </Btn>
              )}
            </div>
          )}
        </Card>

        <Btn onClick={handleDiagnose} disabled={loading || !note.trim()}>
          {loading ? <><Spinner size={16} /> Analyzing…</> : '🔬 Run Diagnostic Analysis'}
        </Btn>

        {error && (
          <div style={{ background: '#2a0e0e', border: '1px solid #4a1e1e', borderRadius: 10, padding: '12px 16px', color: '#f87171', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>

      {/* RIGHT — Results */}
      <div>
        {loading && (
          <Card style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24, padding: '48px 32px' }}>
            <Spinner size={44} />
            <div className="step-list">
              {STEPS.map((s, i) => {
                const state = i < loadStep ? 'done' : i === loadStep ? 'active' : ''
                return (
                  <div key={s.id} className={`step-item ${state}`} style={{ animationDelay: `${i * .12}s` }}>
                    <span className="step-dot" />
                    {i < loadStep ? '✓ ' : ''}{s.label}
                  </div>
                )
              })}
            </div>
          </Card>
        )}
        {result && !loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <ResultsPanel result={result} />
            {result.lab_analysis?.length > 0 && <LabPanel labs={result.lab_analysis} />}
          </div>
        )}
        {!result && !loading && (
          <Card style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '56px 32px' }}>
            <div style={{ fontSize: 44, filter: 'grayscale(1)', opacity: .3 }}>🔬</div>
            <div style={{ color: '#2a4060', fontSize: 14, fontWeight: 700, textAlign: 'center' }}>
              No analysis yet
            </div>
            <div style={{ color: '#1c2d44', fontSize: 12, textAlign: 'center', maxWidth: 260, lineHeight: 1.6 }}>
              Enter a clinical note on the left and click <strong style={{ color: '#3b82f660' }}>Run Diagnostic Analysis</strong> to generate a full AI-powered rare disease report.
            </div>
          </Card>
        )}
      </div>

    </div>
  )
}
