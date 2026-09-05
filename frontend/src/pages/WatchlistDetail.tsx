import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../services/api'
import type { Watchlist } from '../types'
import { Button, Delta, ErrorState, Input, Modal, SeverityPill, Skeleton, fmtPrice } from '../components/ui'

export default function WatchlistDetailPage() {
  const { id } = useParams()
  const nav = useNavigate()
  const [wl, setWl] = useState<Watchlist | null>(null)
  const [err, setErr] = useState('')
  const [filter, setFilter] = useState('All')
  const [addOpen, setAddOpen] = useState(false)
  const [renameOpen, setRenameOpen] = useState(false)
  const [why, setWhy] = useState<{ symbol: string; text: string; score: number } | null>(null)
  const [query, setQuery] = useState('')
  const [hints, setHints] = useState<import('../types').SearchHit[]>([])

  const load = () => api.watchlist(Number(id)).then(setWl).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [id])
  useEffect(() => {
    const t = setTimeout(() => {
      if (!query.trim()) { setHints([]); return }
      api.search(query.trim()).then(setHints).catch(() => setHints([]))
    }, 250)
    return () => clearTimeout(t)
  }, [query])

  if (err) return <ErrorState message={err} />
  if (!wl) return <Skeleton className="h-96" />

  const rows = wl.stocks.filter((s) => {
    const sev = s.quote?.severity
    if (filter === 'Needs Attention') return sev === 'HIGH'
    if (filter === 'Meaningful') return sev === 'MEANINGFUL' || sev === 'NOTABLE'
    if (filter === 'Stable') return sev === 'STABLE'
    return true
  })

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    try {
      setWl(await api.addStock(wl!.id, String(fd.get('symbol'))))
      setAddOpen(false)
      setQuery('')
      setHints([])
    } catch (ex) {
      setErr((ex as Error).message)
    }
  }

  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-[#94A3B8]">My Watchlists / {wl.name}</p>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-[30px] font-semibold">{wl.name}</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setRenameOpen(true)}>Rename</Button>
          <Button variant="outline" onClick={() => setAddOpen(true)}>Add stock</Button>
          <Button variant="ghost" onClick={async () => { await api.deleteWatchlist(wl.id); nav('/app/watchlists') }}>Delete</Button>
        </div>
      </div>
      {wl.stock_count === 0 ? (
        <p className="mt-8 text-sm text-[#94A3B8]">Empty watchlist — add a company name or ticker to start a last-seen baseline.</p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-2">
            {['All', 'Needs Attention', 'Meaningful', 'Stable'].map((f) => (
              <button key={f} onClick={() => setFilter(f)} className={`rounded-full border px-3 py-1 text-xs ${filter === f ? 'border-intel text-primary' : 'border-[#232F46] text-[#94A3B8]'}`}>{f}</button>
            ))}
          </div>
          <div className="mt-4 overflow-x-auto rounded-lg border border-[#232F46]">
            <table className="w-full min-w-[900px] text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-[#94A3B8]">
                <tr>
                  {['Stock & company', 'Price', 'Since last check', 'Today', 'Significance', 'Status', 'Why it matters', 'Actions'].map((h) => (
                    <th key={h} className="px-3 py-2 text-left font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.symbol} className="border-t border-[#232F46] hover:bg-[#1A2234]">
                    <td className="px-3 py-3"><Link className="font-mono" to={`/app/stocks/${s.symbol}`}>{s.symbol}</Link></td>
                    <td className="px-3 py-3 font-mono">{s.quote ? fmtPrice(s.quote.current_price) : '—'}</td>
                    <td className="px-3 py-3"><Delta value={s.quote?.since_last_check_percent} /></td>
                    <td className="px-3 py-3"><Delta value={s.quote?.price_change_percent} /></td>
                    <td className="px-3 py-3 font-mono">{s.quote ? `${s.quote.significance_score}` : '—'}</td>
                    <td className="px-3 py-3">{s.quote ? <SeverityPill severity={s.quote.severity} /> : '—'}</td>
                    <td className="px-3 py-3 max-w-xs truncate text-[#CBD5E1]">{s.quote?.explanation}</td>
                    <td className="px-3 py-3">
                      <button className="text-primary text-xs" onClick={() => s.quote && setWhy({ symbol: s.symbol, text: s.quote.explanation, score: s.quote.significance_score })}>View Why</button>
                      <button className="ml-3 text-loss text-xs" onClick={async () => setWl(await api.removeStock(wl.id, s.symbol))}>Remove</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <Modal open={addOpen} title="Add a company or ticker" onClose={() => { setAddOpen(false); setQuery(''); setHints([]) }}>
        <form onSubmit={add} className="space-y-3">
          <Input name="symbol" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Google, NVIDIA, GOOGL…" required />
          {hints.length > 0 ? (
            <ul className="max-h-40 overflow-auto rounded border border-[#232F46] text-sm">
              {hints.map((h) => (
                <li key={h.symbol}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-[#1A2234]"
                    onClick={async () => {
                      setWl(await api.addStock(wl!.id, h.symbol))
                      setAddOpen(false)
                      setQuery('')
                      setHints([])
                    }}
                  >
                    <span><span className="font-mono">{h.symbol}</span> · {h.company_name}</span>
                    <span className="text-primary">Add</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-[#94A3B8]">Type a company name. We’ll resolve it to a ticker, or pick a match above.</p>
          )}
          <Button type="submit">Add</Button>
        </form>
      </Modal>
      <Modal open={renameOpen} title="Rename watchlist" onClose={() => setRenameOpen(false)}>
        <form className="space-y-3" onSubmit={async (e) => {
          e.preventDefault()
          const fd = new FormData(e.currentTarget)
          setWl(await api.patchWatchlist(wl.id, { name: String(fd.get('name')) }))
          setRenameOpen(false)
        }}>
          <Input name="name" defaultValue={wl.name} /><Button type="submit">Save</Button>
        </form>
      </Modal>
      <Modal open={!!why} title={`${why?.symbol} quantitative signal`} onClose={() => setWhy(null)}>
        <p className="font-mono text-2xl">{why?.score}/100</p>
        <p className="mt-3 text-sm text-[#CBD5E1]">{why?.text}</p>
        <Link to={`/app/stocks/${why?.symbol}`} className="mt-4 inline-block text-sm text-primary">Open full briefing</Link>
      </Modal>
    </div>
  )
}
