import type { Dashboard, Health, HistoryItem, Notification, Quote, SearchHit, Settings, User, Watchlist } from '../types'

const TOKEN_KEY = 'mw_token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let res: Response
  try {
    res = await fetch(`/api${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'network', 'Cannot reach the server. Check your connection and try again.')
  }
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    if (res.status === 401 && data.code === 'session_expired' && !path.startsWith('/auth/')) {
      clearToken()
      window.location.href = '/login?expired=1'
    }
    throw new ApiError(res.status, data.code || 'error', data.message || 'Request failed')
  }
  return data as T
}

const json = (body: unknown) => JSON.stringify(body)

type AuthResponse = { access_token: string; onboarding_complete: boolean }

export const api = {
  health: () => request<Health>('/health'),
  register: (body: { name: string; email: string; password: string }) =>
    request<AuthResponse>('/auth/register', { method: 'POST', body: json(body) }),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>('/auth/login', { method: 'POST', body: json(body) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request<User>('/auth/me'),
  forgot: (email: string) =>
    request<{ ok: boolean; message?: string; reset_url?: string }>('/auth/forgot-password', {
      method: 'POST',
      body: json({ email }),
    }),
  reset: (token: string, password: string) =>
    request('/auth/reset-password', { method: 'POST', body: json({ token, password }) }),
  dashboard: () => request<Dashboard>('/dashboard'),
  checkpoint: () => request<{ ok: boolean; symbols: number; baseline_at: string }>('/dashboard/checkpoint', { method: 'POST' }),
  watchlists: () => request<Watchlist[]>('/watchlists'),
  watchlist: (id: number) => request<Watchlist>(`/watchlists/${id}`),
  createWatchlist: (body: { name: string; category?: string; symbols?: string[] }) =>
    request<Watchlist>('/watchlists', { method: 'POST', body: json(body) }),
  patchWatchlist: (id: number, body: { name?: string; category?: string }) =>
    request<Watchlist>(`/watchlists/${id}`, { method: 'PATCH', body: json(body) }),
  deleteWatchlist: (id: number) => request(`/watchlists/${id}`, { method: 'DELETE' }),
  addStock: (id: number, symbol: string) =>
    request<Watchlist>(`/watchlists/${id}/stocks`, { method: 'POST', body: json({ symbol }) }),
  removeStock: (id: number, symbol: string) =>
    request<Watchlist>(`/watchlists/${id}/stocks/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
  search: (q: string) => request<SearchHit[]>(`/stocks/search?q=${encodeURIComponent(q)}`),
  stock: (symbol: string) => request<Quote>(`/stocks/${encodeURIComponent(symbol)}`),
  history: (opts: { severity?: string; symbol?: string; cursor?: number | null } = {}) => {
    const p = new URLSearchParams()
    if (opts.severity) p.set('severity', opts.severity)
    if (opts.symbol) p.set('symbol', opts.symbol)
    if (opts.cursor) p.set('cursor', String(opts.cursor))
    return request<{ items: HistoryItem[]; next_cursor: number | null }>(`/changes/history?${p.toString()}`)
  },
  settings: () => request<Settings>('/settings'),
  patchSettings: (body: Partial<Settings>) => request<Settings>('/settings', { method: 'PATCH', body: json(body) }),
  notifications: () => request<Notification[]>('/notifications'),
  markNotificationsRead: () => request('/notifications/read', { method: 'POST' }),
}
