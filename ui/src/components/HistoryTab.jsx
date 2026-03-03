import { useState } from 'react'
import { api } from '../api.js'
import { Card, CardTitle, Btn, Input, Badge, Spinner, Divider } from './ui.jsx'

function urgencyColor(u) {
  if (!u) return 'gray'
  const l = u.toLowerCase()
  if (l.includes('emergency')) return 'red'
  if (l.includes('urgent')) return 'orange'
  return 'green'
}

function CaseRow({ c, onView }) {
  const conf = c.confidence ? Math.round(c.confidence * 100) : null
  return (
    <div className="case-row" onClick={() => onView(c)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: '#d4e2f5', fontWeight: 600, fontSize: 13, marginBottom: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {c.top_diagnosis || 'No diagnosis'}
          </div>
          <div style={{ fontSize: 11, color: '#2a4060' }}>
            {c.timestamp ? new Date(c.timestamp).toLocaleString() : ''} · case #{c.id}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
          {c.urgency && <Badge color={urgencyColor(c.urgency)}>{c.urgency}</Badge>}
          {conf !== null && (
            <span style={{ fontSize: 12, color: conf >= 70 ? '#34d399' : '#f97316', fontWeight: 700 }}>
              {conf}%
            </span>
          )}
          <span style={{ color: '#2a4060', fontSize: 12 }}>→</span>
        </div>
      </div>
      {c.clinical_note && (
        <div style={{ marginTop: 6, fontSize: 11, color: '#334d68', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
          {c.clinical_note}
        </div>
      )}
    </div>
  )
}

export default function HistoryTab({ onViewCase }) {
  const [patientId, setPatientId] = useState('')
  const [cases, setCases] = useState([])
  const [patients, setPatients] = useState([])
  const [mode, setMode] = useState(null) // 'patient' | 'all'
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadPatient = async () => {
    if (!patientId.trim()) return
    setLoading(true); setError(null)
    try {
      const r = await api.patientHistory(patientId.trim())
      setCases(r.cases || r || [])
      setMode('patient')
    } catch { setError('No records found for that patient ID') }
    setLoading(false)
  }

  const loadAll = async () => {
    setLoading(true); setError(null)
    try {
      const r = await api.listPatients()
      setPatients(r.patients || r || [])
      setMode('all')
    } catch { setError('Could not load patients') }
    setLoading(false)
  }

  const loadCase = async (c) => {
    try {
      const detail = await api.getCase(c.id)
      const result = typeof detail.result_json === 'string'
        ? JSON.parse(detail.result_json) : detail.result_json
      onViewCase(result)
    } catch { onViewCase(null) }
  }

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <Card style={{ marginBottom: 20 }}>
        <CardTitle>Patient Case History</CardTitle>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <Input
            value={patientId}
            onChange={setPatientId}
            placeholder="Enter patient ID…"
            style={{ flex: 1, minWidth: 200 }}
            onKeyDown={e => e.key === 'Enter' && loadPatient()}
          />
          <Btn variant="secondary" onClick={loadPatient} small disabled={!patientId.trim() || loading}>
            Load History
          </Btn>
          <Btn variant="ghost" onClick={loadAll} small disabled={loading}>
            All Patients
          </Btn>
        </div>
      </Card>

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

      {/* Patient list (all mode) */}
      {mode === 'all' && !loading && (
        <Card>
          <CardTitle>All Patients ({patients.length})</CardTitle>
          {patients.length === 0 && (
            <div style={{ color: '#2a4060', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>No patients on record yet.</div>
          )}
          {patients.map(p => (
            <div key={p.patient_id} style={{ padding: '10px 0', borderBottom: '1px solid #1c2d44' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ color: '#60a5fa', fontWeight: 600, fontSize: 13 }}>{p.patient_id}</span>
                  <span style={{ color: '#2a4060', fontSize: 11, marginLeft: 10 }}>{p.case_count} case{p.case_count !== 1 ? 's' : ''}</span>
                </div>
                <Btn variant="ghost" small onClick={() => { setPatientId(p.patient_id); setCases([]); setMode(null); }}>
                  View →
                </Btn>
              </div>
            </div>
          ))}
        </Card>
      )}

      {/* Cases for a patient */}
      {mode === 'patient' && !loading && (
        <Card>
          <CardTitle>Cases for "{patientId}" ({cases.length})</CardTitle>
          {cases.length === 0 && (
            <div style={{ color: '#2a4060', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>No cases found.</div>
          )}
          {cases.map(c => <CaseRow key={c.id} c={c} onView={loadCase} />)}
        </Card>
      )}

      {!mode && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: '56px 32px' }}>
          <div style={{ fontSize: 40, opacity: .2 }}>📂</div>
          <div style={{ color: '#1c2d44', fontSize: 13, textAlign: 'center', maxWidth: 300 }}>
            Enter a patient ID above or click <strong style={{ color: '#2a4060' }}>All Patients</strong> to browse diagnostic history.
          </div>
        </div>
      )}
    </div>
  )
}
