import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api, clearToken } from '../services/api'
import type { Health, User } from '../types'
import { cn } from '../utils/cn'
import { MARKET_LABEL } from '../utils/format'

const links = [
  { to: '/app/overview', label: 'Overview' },
  { to: '/app/watchlists', label: 'My Watchlists' },
  { to: '/app/discover', label: 'Discover' },
  { to: '/app/history', label: 'Change History' },
  { to: '/app/settings', label: 'Settings' },
]

export default function AppShell() {
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [me, setMe] = useState<User | null>(null)
  const [health, setHealth] = useState<Health | null>(null)

  useEffect(() => {
    api.me().then(setMe).catch(() => undefined)
    api.health().then(setHealth).catch(() => undefined)
    const t = setInterval(() => api.health().then(setHealth).catch(() => undefined), 60_000)
    return () => clearInterval(t)
  }, [])

  const marketOpen = health?.market_state === 'OPEN'

  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <aside className={cn(
        'fixed inset-y-0 left-0 z-50 flex w-72 flex-col justify-between bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.4)] transition-transform md:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      )}>
        <div>
          <div className="flex h-16 items-center gap-2 px-5">
            <img src="/logo.svg" alt="Smart Market Watch" className="h-8" />
          </div>
          <p className="px-5 pb-3 text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">What changed since you last looked</p>
          <nav className="flex flex-col gap-1 px-3">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  cn('rounded px-3 py-2 text-sm', isActive ? 'bg-surface-container-high text-on-surface' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface')
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="p-4">
          <div className="rounded-lg border border-[#232F46] bg-surface-container p-3">
            <p className={cn('text-xs', marketOpen ? 'text-gain' : 'text-on-surface-variant')}>
              {health ? MARKET_LABEL[health.market_state] ?? health.market_state : 'Checking market…'}
            </p>
            {health ? (
              <p className="mt-1 font-mono text-[11px] text-on-surface-variant">
                {health.provider} · cache {health.cache}
              </p>
            ) : null}
            <p className="mt-2 truncate text-sm font-medium">{me?.name ?? '…'}</p>
            <p className="truncate text-xs text-on-surface-variant">{me?.email ?? ''}</p>
          </div>
        </div>
      </aside>
      <div className="md:pl-72">
        {health?.persistence === 'ephemeral' ? (
          <div className="border-b border-warn/30 bg-warn/10 px-4 py-2 text-xs text-warn">
            Demo deployment without a durable database: accounts and baselines can reset when the server recycles. Set DATABASE_URL for persistence.
          </div>
        ) : null}
        <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-[#232F46] bg-surface/90 px-4 py-3 backdrop-blur">
          <button className="md:hidden text-on-surface" onClick={() => setOpen((v) => !v)} aria-label="Toggle navigation">☰</button>
          <form
            className="relative flex-1"
            onSubmit={(e) => {
              e.preventDefault()
              if (q.trim()) nav(`/app/discover?q=${encodeURIComponent(q.trim())}`)
            }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search a company or ticker (Google, NVDA…)"
              className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm"
              aria-label="Search stocks"
            />
          </form>
          <button onClick={() => nav('/app/notifications')} className="text-sm text-on-surface-variant">Alerts</button>
          <button
            onClick={() => {
              api.logout().catch(() => undefined)
              clearToken()
              nav('/login')
            }}
            className="text-sm text-on-surface-variant"
          >
            Sign out
          </button>
        </header>
        {open ? <button className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setOpen(false)} aria-label="Close navigation" /> : null}
        <main className="px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
