// Shared low-level UI primitives

export function Card({ children, style, glow, noPad }) {
  return (
    <div style={{
      background: '#0a1424',
      border: `1px solid ${glow ? '#2a4060' : '#1c2d44'}`,
      borderRadius: 14,
      padding: noPad ? 0 : '18px 20px',
      boxShadow: glow
        ? '0 0 0 1px #3b82f620, 0 8px 40px rgba(0,0,0,.7), 0 0 28px #3b82f612'
        : '0 2px 20px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.015)',
      transition: 'box-shadow .2s',
      ...style,
    }}>
      {children}
    </div>
  )
}

export function CardTitle({ children, style }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 800, textTransform: 'uppercase',
      letterSpacing: '.12em', color: '#334d68', marginBottom: 14,
      ...style,
    }}>
      {children}
    </div>
  )
}

export function Btn({ children, onClick, disabled, variant = 'primary', style, small }) {
  const isP = variant === 'primary'
  const base = {
    border: 'none', borderRadius: small ? 8 : 11,
    fontWeight: 700, cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? .36 : 1,
    fontSize: small ? 12 : 14,
    padding: small ? '7px 14px' : '12px 22px',
    display: 'inline-flex', alignItems: 'center', justifyContent: isP ? 'center' : undefined, gap: 7,
    transition: 'opacity .15s, transform .1s, box-shadow .15s',
    width: isP ? '100%' : undefined,
    ...style,
  }
  const v = {
    primary:   { background: 'linear-gradient(135deg, #1d5ce6, #7c3aed)', color: '#fff', fontSize: 15, padding: '13px', boxShadow: '0 4px 22px rgba(59,130,246,.35)' },
    secondary: { background: '#0d1829', border: '1px solid #1c2d44', color: '#6a87a8' },
    ghost:     { background: 'transparent', border: '1px solid #1c2d44', color: '#6a87a8' },
    danger:    { background: '#180404', border: '1px solid #361010', color: '#ef4444' },
  }
  return (
    <button
      onClick={disabled ? undefined : onClick}
      style={{ ...base, ...v[variant] }}
      onMouseEnter={e => { if (!disabled && isP) e.currentTarget.style.boxShadow = '0 6px 34px rgba(59,130,246,.6)' }}
      onMouseLeave={e => { if (isP) e.currentTarget.style.boxShadow = '0 4px 22px rgba(59,130,246,.35)' }}
    >
      {children}
    </button>
  )
}

export function Input({ value, onChange, placeholder, style, onKeyDown }) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      onKeyDown={onKeyDown}
      style={{
        background: '#060a10', border: '1px solid #1c2d44',
        borderRadius: 8, color: '#d4e2f5', fontSize: 13,
        padding: '8px 12px', outline: 'none', width: '100%',
        transition: 'border-color .15s',
        ...style,
      }}
      onFocus={e => e.target.style.borderColor = '#3b82f6'}
      onBlur={e  => e.target.style.borderColor = '#1c2d44'}
    />
  )
}

export function Textarea({ value, onChange, placeholder, rows = 8, style }) {
  return (
    <textarea
      rows={rows}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        width: '100%', background: '#060a10',
        border: '1px solid #1c2d44',
        borderRadius: 10, color: '#d4e2f5', fontSize: 13, lineHeight: 1.72,
        padding: '13px 14px', outline: 'none', resize: 'vertical',
        fontFamily: 'inherit', transition: 'border-color .15s',
        ...style,
      }}
      onFocus={e => e.target.style.borderColor = '#3b82f6'}
      onBlur={e  => e.target.style.borderColor = '#1c2d44'}
    />
  )
}

export function Badge({ children, color = 'gray' }) {
  const cls = `badge badge-${color}`
  return <span className={cls}>{children}</span>
}

export function Spinner({ size = 32 }) {
  return (
    <div style={{
      width: size, height: size,
      border: `${size > 20 ? 3 : 2}px solid #1c2d44`,
      borderTopColor: '#3b82f6',
      borderRadius: '50%',
      animation: 'spin .7s linear infinite',
      flexShrink: 0,
    }} />
  )
}

export function Divider({ style }) {
  return <div style={{ height: 1, background: '#1c2d44', margin: '12px 0', ...style }} />
}

export function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 800, color: '#334d68',
      textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: 10,
    }}>{children}</div>
  )
}

