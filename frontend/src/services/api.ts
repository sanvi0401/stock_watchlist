const TOKEN_KEY = 'mw_token'
const IDENTITY_KEY = 'mw_identity'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getIdentity() {
  return localStorage.getItem(IDENTITY_KEY)
}

export function setIdentity(token?: string | null) {
  if (token) localStorage.setItem(IDENTITY_KEY, token)
}

export function clearIdentity() {
  localStorage.removeItem(IDENTITY_KEY)
}

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function captureIdentity(data: unknown) {
  if (Array.isArray(data)) {
    data.forEach(captureIdentity)
    return
  }
  if (data && typeof data === 'object' && 'identity_token' in data) {
    const token = (data as { identity_token?: string }).identity_token
    if (token) setIdentity(token)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const identity = getIdentity()
  if (identity) headers.set('X-Identity-Backup', identity)
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    if (res.status === 401 && data.code === 'session_expired' && !path.startsWith('/auth/')) {
      clearToken()
      window.location.href = '/login?expired=1'
    }
    throw new ApiError(res.status, data.code || 'error', data.message || 'Request failed')
  }
  captureIdentity(data)
  return data as T
}

export const api = {
  register: (body: { name: string; email: string; password: string }) =>
    request<{ access_token: string; onboarding_complete: boolean; identity_token?: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    request<{ access_token: string; onboarding_complete: boolean; identity_token?: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ ...body, identity_backup: getIdentity() }),
    }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  forgot: (email: string) =>
    request<{ ok: boolean; message?: string; reset_url?: string; dev_reset_token?: string }>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email, identity_backup: getIdentity() }),
    }),
  reset: (token: string, password: string) =>
    request('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, password }) }),
  dashboard: () => request<import('../types').Dashboard>('/dashboard'),
  watchlists: () => request<import('../types').Watchlist[]>('/watchlists'),
  watchlist: (id: number) => request<import('../types').Watchlist>(`/watchlists/${id}`),
  createWatchlist: (body: { name: string; category?: string; symbols?: string[] }) =>
    request<import('../types').Watchlist>('/watchlists', { method: 'POST', body: JSON.stringify(body) }),
  patchWatchlist: (id: number, body: { name?: string }) =>
    request<import('../types').Watchlist>(`/watchlists/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteWatchlist: (id: number) => request(`/watchlists/${id}`, { method: 'DELETE' }),
  addStock: (id: number, symbol: string) =>
    request<import('../types').Watchlist>(`/watchlists/${id}/stocks`, {
      method: 'POST',
      body: JSON.stringify({ symbol }),
    }),
  removeStock: (id: number, symbol: string) =>
    request<import('../types').Watchlist>(`/watchlists/${id}/stocks/${symbol}`, { method: 'DELETE' }),
  search: (q: string) => request<import('../types').SearchHit[]>(`/stocks/search?q=${encodeURIComponent(q)}`),
  stock: (symbol: string) => request<import('../types').Quote>(`/stocks/${symbol}`),
  history: (severity?: string, cursor?: number) => {
    const p = new URLSearchParams()
    if (severity) p.set('severity', severity)
    if (cursor) p.set('cursor', String(cursor))
    return request<{ items: import('../types').HistoryItem[]; next_cursor: number | null }>(
      `/changes/history?${p.toString()}`,
    )
  },
  settings: () => request('/settings'),
  patchSettings: (body: Record<string, unknown>) =>
    request('/settings', { method: 'PATCH', body: JSON.stringify(body) }),
  notifications: () =>
    request<Array<{ id: number; title: string; body: string; read: boolean; created_at: string; kind: string }>>(
      '/notifications',
    ),
}

export type SearchHit = {
  symbol: string
  company_name: string
  current_price: number | null
  price_change_percent: number | null
  data_status: string
  market_state: string
}
