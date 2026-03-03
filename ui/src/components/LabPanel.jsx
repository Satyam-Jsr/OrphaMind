import { Card, CardTitle } from './ui.jsx'

function rowClass(status) {
  if (status === 'CRITICAL HIGH' || status === 'CRITICAL LOW') return 'lab-row-crit'
  if (status === 'HIGH') return 'lab-row-high'
  if (status === 'LOW')  return 'lab-row-low'
  return ''
}

function statusMeta(status) {
  switch (status) {
    case 'CRITICAL HIGH': return { color: '#ef4444', bg: '#1e0404', border: '#3a0a0a', icon: '🚨' }
    case 'CRITICAL LOW':  return { color: '#ef4444', bg: '#1e0404', border: '#3a0a0a', icon: '🚨' }
    case 'HIGH':          return { color: '#f97316', bg: '#1a0c04', border: '#3a1a06', icon: '▲' }
    case 'LOW':           return { color: '#60a5fa', bg: '#040e1e', border: '#0a1e40', icon: '▼' }
    default:              return { color: '#34d399', bg: '#051209', border: '#0a2a14', icon: '✓' }
  }
}

function FoldBadge({ fold }) {
  if (!fold || fold <= 1.2) return null
  const color = fold >= 5 ? '#ef4444' : fold >= 2 ? '#f97316' : '#f59e0b'
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, color,
      background: '#100a02', border: `1px solid ${color}35`,
      borderRadius: 6, padding: '1px 6px', marginLeft: 6,
    }}>
      ×{fold.toFixed(1)} ULN
    </span>
  )
}

export default function LabPanel({ labs }) {
  if (!labs?.length) return null
  const abnormal = labs.filter(l => l.status !== 'NORMAL')
  const normal   = labs.filter(l => l.status === 'NORMAL')
  const sorted   = [...abnormal, ...normal]

  return (
    <Card noPad>
      <div style={{ padding: '18px 20px 12px' }}>
        <CardTitle style={{ marginBottom: 0 }}>
          Lab Analysis — {labs.length} values · <span style={{ color: abnormal.length > 0 ? '#f97316' : '#34d399' }}>{abnormal.length} abnormal</span>
        </CardTitle>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#08111e', borderBottom: '1px solid #1c2d44' }}>
              {['Test', 'Value', 'Reference Range', 'Status'].map(h => (
                <th key={h} style={{
                  textAlign: 'left', padding: '8px 12px',
                  color: '#2a4060', fontWeight: 700,
                  textTransform: 'uppercase', letterSpacing: '.08em', fontSize: 10,
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((lab, i) => {
              const m = statusMeta(lab.status)
              return (
                <tr key={i} className={rowClass(lab.status)} style={{
                  borderBottom: '1px solid #0f1c2e',
                  background: i % 2 === 0 ? 'transparent' : '#060e1a',
                }}>
                  <td style={{ padding: '8px 12px', color: '#c8d8ea', fontWeight: 600 }}>{lab.name}</td>
                  <td style={{ padding: '8px 12px', color: '#d4e2f5' }}>
                    {lab.value} {lab.unit}
                    {lab.fold_change && <FoldBadge fold={lab.fold_change} />}
                  </td>
                  <td style={{ padding: '8px 12px', color: '#334d68' }}>{lab.normal_range || '—'}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      background: m.bg, color: m.color,
                      border: `1px solid ${m.border}`,
                      borderRadius: 8, padding: '2px 9px', fontSize: 10, fontWeight: 700,
                    }}>
                      {m.icon} {lab.status || 'NORMAL'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
