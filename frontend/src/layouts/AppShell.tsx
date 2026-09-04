import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api, clearToken, getToken } from '../services/api'
import { cn } from '../components/ui'

const links = [
  { to: '/app/overview', label: 'Overview', icon: 'dashboard' },
  { to: '/app/watchlists', label: 'My Watchlists', icon: 'view_list' },
  { to: '/app/discover', label: 'Discover / Signals', icon: 'radar' },
  { to: '/app/history', label: 'Change History', icon: 'history' },
  { to: '/app/settings', label: 'Settings', icon: 'tune' },
]

export default function AppShell() {
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [name, setName] = useState('Analyst')

  useEffect(() => {
    if (!getToken()) nav('/login')
    api.me().then((u) => setName((u as { name: string }).name)).catch(() => undefined)
  }, [nav])

  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <aside className={cn(
        'fixed inset-y-0 left-0 z-50 flex w-72 flex-col justify-between bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.4)] transition-transform md:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      )}>
        <div>
          <div className="flex h-16 items-center gap-2 px-5">
            <img src="/logo.svg" alt="Market Watch" className="h-8" />
          </div>
          <p className="px-5 pb-3 text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">Quantitative Engine</p>
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
            <p className="text-xs text-gain">US Markets Open</p>
            <p className="mt-2 text-sm font-medium">{name}</p>
            <p className="text-xs text-on-surface-variant">Pro Plan · Analyst</p>
          </div>
        </div>
      </aside>
      <div className="md:pl-72">
        <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-[#232F46] bg-surface/90 px-4 py-3 backdrop-blur">
          <button className="md:hidden text-on-surface" onClick={() => setOpen((v) => !v)}>☰</button>
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
              placeholder="Search stocks, tickers, or anomaly tags (e.g. NVDA, high volume)..."
              className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 pr-12 text-sm"
            />
            <span className="absolute right-2 top-1.5 rounded bg-[#1A2234] px-1.5 font-mono text-[11px] text-[#94A3B8]">⌘K</span>
          </form>
          <button onClick={() => nav('/app/notifications')} className="text-sm text-on-surface-variant">Alerts</button>
          <button
            onClick={() => {
              clearToken()
              nav('/login')
            }}
            className="text-sm text-on-surface-variant"
          >
            Sign out
          </button>
        </header>
        {open ? <button className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setOpen(false)} /> : null}
        <main className="px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
