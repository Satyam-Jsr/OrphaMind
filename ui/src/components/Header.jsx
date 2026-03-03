export default function Header({ health }) {
  const isOnline  = health?.status === 'healthy'
  const isOffline = health?.status === 'offline'
  const dotColor  = isOnline ? '#34d399' : isOffline ? '#ef4444' : '#f59e0b'

  const statusText = health
    ? isOnline
      ? `${(health.llm_backend || 'gemini').toUpperCase()} · Online`
      : isOffline ? 'Offline — start backend' : 'Degraded'
    : 'Connecting…'

  return (
    <header style={{
      background: 'linear-gradient(180deg, #09101e 0%, #060a10 100%)',
      borderBottom: '1px solid #1c2d44',
      padding: '0 28px',
      height: 60,
      display: 'flex', alignItems: 'center', gap: 14,
      position: 'sticky', top: 0, zIndex: 200,
      backdropFilter: 'blur(16px)',
    }}>
      {/* Logo mark */}
      <div style={{
        width: 38, height: 38, borderRadius: 12, flexShrink: 0,
        background: 'linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18,
        boxShadow: '0 0 0 1px #3b82f630, 0 4px 22px #3b82f640',
      }}>🧬</div>

      {/* Brand name */}
      <div>
        <div style={{ fontSize: 16, fontWeight: 800, color: '#d4e2f5', letterSpacing: '-.02em', lineHeight: 1 }}>
          OrphaMind
        </div>
        <div style={{ fontSize: 10, color: '#2a4060', marginTop: 3, textTransform: 'uppercase', letterSpacing: '.12em', fontWeight: 600 }}>
          Rare Disease AI · v2.0
        </div>
      </div>

      {/* Separator */}
      <div style={{ width: 1, height: 32, background: '#1c2d44', marginLeft: 8, flexShrink: 0 }} />

      {/* Centre stats */}
      {isOnline && (
        <div style={{ display: 'flex', gap: 0, flexShrink: 0 }}>
          {[
            { v: (health.diseases_loaded || 11456).toLocaleString(), l: 'diseases' },
            { v: '87,848', l: 'lit docs' },
            { v: '4 layers', l: 'guard' },
          ].map(({ v, l }, i) => (
            <div key={i} style={{
              textAlign: 'center', padding: '0 16px',
              borderRight: i < 2 ? '1px solid #1c2d44' : 'none',
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#60a5fa', lineHeight: 1 }}>{v}</div>
              <div style={{ fontSize: 9, color: '#2a4060', textTransform: 'uppercase', letterSpacing: '.1em', marginTop: 3 }}>{l}</div>
            </div>
          ))}
        </div>
      )}

      {/* Status pill — pushed to right */}
      <div style={{
        marginLeft: 'auto',
        display: 'flex', alignItems: 'center', gap: 7,
        background: '#060e1c',
        border: `1px solid ${isOnline ? '#173828' : isOffline ? '#2a0e0e' : '#2a2004'}`,
        borderRadius: 20, padding: '5px 14px', fontSize: 12,
        flexShrink: 0,
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: dotColor, boxShadow: `0 0 8px ${dotColor}`,
          flexShrink: 0,
          animation: isOnline ? 'pulse 2.4s infinite' : 'none',
        }} />
        <span style={{ color: dotColor, fontWeight: 600 }}>{statusText}</span>
      </div>
    </header>
  )
}
