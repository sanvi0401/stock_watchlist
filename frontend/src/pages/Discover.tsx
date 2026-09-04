import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { SearchHit, Watchlist } from '../types'
import { Button, Card, DataBadge, Delta, ErrorState, ExchangeTag, Input } from '../components/ui'
import { fmtPrice } from '../utils/format'

const QUICK_ADD = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'NVDA', 'AAPL', 'MSFT', 'TSLA']

type Searched = { term: string; hits: SearchHit[] }

export default function DiscoverPage({ initialQuery = '' }: { initialQuery?: string }) {
  const [q, setQ] = useState(initialQuery)
  const [searched, setSearched] = useState<Searched>({ term: '', hits: [] })
  const [lists, setLists] = useState<Watchlist[]>([])
  const [listId, setListId] = useState<number | ''>('')
  const [err, setErr] = useState('')
  const [notice, setNotice] = useState('')
  const [adding, setAdding] = useState<string | null>(null)
  const term = q.trim()
  const loading = term !== '' && searched.term !== term
  const hits = term ? searched.hits : []

  useEffect(() => {
    api.watchlists().then((rows) => {
      setLists(rows)
      if (rows[0]) setListId(rows[0].id)
    }).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!term) return
    let cancelled = false
    const t = setTimeout(() => {
      api.search(term)
        .then((rows) => { if (!cancelled) { setSearched({ term, hits: rows }); setErr('') } })
        .catch((e) => { if (!cancelled) { setSearched({ term, hits: [] }); setErr(e.message) } })
    }, 280)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [term])

  const selected = lists.find((l) => l.id === listId)
  const onList = (symbol: string) => selected?.stocks.some((s) => s.symbol === symbol) ?? false

  async function addSymbol(symbol: string) {
    setErr('')
    setNotice('')
    setAdding(symbol)
    try {
      if (!selected) {
        const created = await api.createWatchlist({ name: 'My Watchlist', category: 'Core', symbols: [symbol] })
        setLists((prev) => [created, ...prev])
        setListId(created.id)
        setNotice(`Created "My Watchlist" with ${symbol}. Its current price is now your baseline.`)
      } else {
        const updated = await api.addStock(selected.id, symbol)
        setLists((prev) => prev.map((l) => (l.id === updated.id ? updated : l)))
        setNotice(`${symbol} added to ${updated.name}. Its current price is now your baseline.`)
      }
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setAdding(null)
    }
  }

  return (
    <div>
      <h1 className="text-[30px] font-semibold">Discover</h1>
      <p className="mt-1 text-sm text-[#94A3B8]">
        Any exchange Yahoo covers: search by company name (“Reliance”, “Google”) or ticker (RELIANCE.NS, TCS.BO, GOOGL, VOD.L). Adding a name records the price you saw as its baseline.
      </p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search Reliance, Infosys, NVIDIA, Apple…" aria-label="Search" /></div>
        {lists.length > 0 ? (
          <label className="text-sm text-[#94A3B8]">
            Add to
            <select
              className="ml-2 h-10 rounded border border-[#232F46] bg-[#0B0F17] px-2 text-on-surface"
              value={listId}
              onChange={(e) => setListId(Number(e.target.value))}
            >
              {lists.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </label>
        ) : (
          <p className="text-xs text-[#94A3B8]">Your first add creates “My Watchlist”.</p>
        )}
      </div>
      {notice ? <p className="mt-3 text-sm text-gain">{notice}</p> : null}
      {err ? <div className="mt-4"><ErrorState message={err} /></div> : null}
      {loading ? <p className="mt-4 text-sm text-[#94A3B8]">Searching…</p> : null}
      {!loading && q && hits.length === 0 && !err ? <p className="mt-4 text-sm text-[#94A3B8]">No results. Try the company name or the exact ticker.</p> : null}
      <div className="mt-4 grid gap-3">
        {hits.map((h) => (
          <Card key={h.symbol} className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <Link to={`/app/stocks/${h.symbol}`} className="font-mono text-lg">{h.symbol}</Link> <ExchangeTag name={h.exchange_name} state={h.market_state} />
              <p className="text-sm text-[#94A3B8]">{h.company_name}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono">{h.current_price != null ? fmtPrice(h.current_price, h.currency) : '—'}</span>
              <Delta value={h.price_change_percent} />
              <DataBadge status={h.data_status} />
              <Button className="shrink-0" variant="outline" disabled={adding === h.symbol || onList(h.symbol)} onClick={() => addSymbol(h.symbol)}>
                {onList(h.symbol) ? 'Added' : adding === h.symbol ? 'Adding…' : 'Add'}
              </Button>
            </div>
          </Card>
        ))}
      </div>
      <h2 className="mt-10 text-lg font-semibold">Quick add</h2>
      <p className="mt-1 text-sm text-[#94A3B8]">Widely followed NSE and US large caps, useful for trying the product quickly. Not a recommendation.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {QUICK_ADD.map((t) => (
          <Button key={t} variant="outline" disabled={adding === t || onList(t)} onClick={() => addSymbol(t)}>
            {onList(t) ? `${t} ✓` : `Add ${t}`}
          </Button>
        ))}
      </div>
    </div>
  )
}
