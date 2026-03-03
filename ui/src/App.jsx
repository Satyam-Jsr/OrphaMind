import { useState, useEffect, useCallback } from 'react'
import './global.css'
import { api } from './api.js'
import Header from './components/Header.jsx'
import DiagnoseTab from './components/DiagnoseTab.jsx'
import HistoryTab from './components/HistoryTab.jsx'
import SearchTab from './components/SearchTab.jsx'

const TABS = [
  { id: 'diagnose', label: '🔬 Diagnose' },
  { id: 'history',  label: '📋 History'  },
  { id: 'search',   label: '🔎 Search'   },
]

export default function App() {
  const [tab, setTab]         = useState('diagnose')
  const [health, setHealth]   = useState(null)
  // loadCase: { result, note, loadId } — changes trigger DiagnoseTab to load a history case
  const [loadCase, setLoadCase] = useState(null)

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch(() => setHealth({ status: 'offline' }))
  }, [])

  const viewCase = useCallback((caseData) => {
    setLoadCase({ result: caseData, note: caseData?.clinical_note || '', loadId: Date.now() })
    setTab('diagnose')
    setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }), 100)
  }, [])

  const s = {
    app: { minHeight: '100vh', display: 'flex', flexDirection: 'column' },
    main: { flex: 1, maxWidth: 1340, margin: '0 auto', width: '100%', padding: '20px 20px' },
    tabBar: {
      display: 'flex', gap: 2, marginBottom: 24,
      borderBottom: '1px solid #1c2d44', paddingBottom: 0,
    },
    tab: (active) => ({
      padding: '10px 24px',
      background: active ? '#08111e' : 'transparent',
      border: 'none',
      borderBottom: active ? '2px solid #3b82f6' : '2px solid transparent',
      borderRadius: active ? '8px 8px 0 0' : 0,
      color: active ? '#d4e2f5' : '#334d68',
      fontSize: 14, fontWeight: 600, cursor: 'pointer',
      transition: 'color .15s, border-color .15s, background .15s',
      marginBottom: -1,
      whiteSpace: 'nowrap',
    }),
  }

  return (
    <div style={s.app}>
      <Header health={health} />
      <main style={s.main}>
        <div style={s.tabBar}>
          {TABS.map(t => (
            <button key={t.id} style={s.tab(tab === t.id)} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {/* All tabs always mounted — CSS hides inactive ones to preserve state */}
        <div style={{ display: tab === 'diagnose' ? undefined : 'none' }}>
          <DiagnoseTab loadCase={loadCase} />
        </div>
        <div style={{ display: tab === 'history' ? undefined : 'none' }}>
          <HistoryTab onViewCase={viewCase} />
        </div>
        <div style={{ display: tab === 'search' ? undefined : 'none' }}>
          <SearchTab />
        </div>
      </main>
    </div>
  )
}
