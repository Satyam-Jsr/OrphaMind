// Centralised API client — proxied via Vite to http://localhost:8000
const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export const api = {
  health: () => req('/health'),
  diagnose: (body) => req('/diagnose', { method: 'POST', body: JSON.stringify(body) }),
  validateNote: (text) => req('/validate-note', { method: 'POST', body: JSON.stringify({ text }) }),
  analyzeLabs: (text) => req('/analyze-labs', { method: 'POST', body: JSON.stringify({ text }) }),
  searchDiseases: (query, limit = 15) => req(`/diseases/search?query=${encodeURIComponent(query)}&limit=${limit}`),
  getDisease: (id) => req(`/diseases/${id}`),
  listPatients: () => req('/patients'),
  patientHistory: (id, limit = 20) => req(`/patients/${encodeURIComponent(id)}/history?limit=${limit}`),
  getCase: (id) => req(`/cases/${id}`),
  ocrNote: (file, noteType = 'typed') => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/ocr-note?note_type=${noteType}`, { method: 'POST', body: form }).then(r => r.json())
  },
}
