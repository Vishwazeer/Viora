const API_BASE = import.meta.env.VITE_API_URL || ''
const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY; if (!ADMIN_KEY) { console.error('SECURITY WARNING: VITE_ADMIN_KEY is not set'); }

const headers = () => ({
  'Content-Type': 'application/json',
  'X-Admin-Key': ADMIN_KEY,
})

export async function fetchStats() {
  const r = await fetch(`${API_BASE}/dashboard/stats`, { headers: headers() })
  if (!r.ok) throw new Error('Failed to fetch stats')
  return r.json()
}

export async function fetchCalls(params = {}) {
  const q = new URLSearchParams(params).toString()
  const r = await fetch(`${API_BASE}/dashboard/calls?${q}`, { headers: headers() })
  if (!r.ok) throw new Error('Failed to fetch calls')
  return r.json()
}

export async function fetchCall(id) {
  const r = await fetch(`${API_BASE}/dashboard/calls/${id}`, { headers: headers() })
  if (!r.ok) throw new Error('Call not found')
  return r.json()
}

export async function fetchEscalations(params = {}) {
  const q = new URLSearchParams(params).toString()
  const r = await fetch(`${API_BASE}/dashboard/escalations?${q}`, { headers: headers() })
  if (!r.ok) throw new Error('Failed to fetch escalations')
  return r.json()
}

export async function fetchHealthStatus() {
  const r = await fetch(`${API_BASE}/dashboard/health-status`, { headers: headers() })
  if (!r.ok) throw new Error('Failed to fetch health status')
  return r.json()
}

export async function fetchConfig() {
  const r = await fetch(`${API_BASE}/admin/config`, { headers: headers() })
  if (!r.ok) throw new Error('Failed to fetch config')
  return r.json()
}

export async function fetchFlags() {
  const r = await fetch(`${API_BASE}/admin/flags`, { headers: headers() })
  if (!r.ok) throw new Error('Failed to fetch flags')
  return r.json()
}

export async function patchFlag(flag, enabled) {
  const r = await fetch(`${API_BASE}/admin/flags/${flag}?enabled=${enabled}`, {
    method: 'PATCH',
    headers: headers(),
  })
  if (!r.ok) throw new Error('Failed to update flag')
  return r.json()
}
