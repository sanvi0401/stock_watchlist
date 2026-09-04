import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import type { SearchHit, Watchlist } from '../types'
import { Button, Card, Delta, ErrorState, Input, fmtPrice } from '../components/ui'

export default function DiscoverPage() {
  const [params] = useSearchParams()
  const [q, setQ] = useState(params.get('q') || '')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [lists, setLists] = useState<Watchlist[]>([])
  const [listId, setListId] = useState<number | ''>('')
  const [err, setErr] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [adding, setAdding] = useState<string | null>(null)

  useEffect(() => {
    api.watchlists().then((rows) => {
      setLists(rows)
      if (rows[0]) setListId(rows[0].id)
    }).catch(() => undefined)
  }, [])
  useEffect(() => {
    const t = setTimeout(() => {
      if (!q.trim()) { setHits([]); return }
      setLoading(true)
      setErr('')
      api.search(q.trim()).then(setHits).catch((e) => setErr(e.message)).finally(() => setLoading(false))
    }, 280)
    return () => clearTimeout(t)
  }, [q])

  const selected = lists.find((l) => l.id === listId)
  const clusters = useMemo(() => [
    { title: 'Unusual Institutional Flow', tickers: ['NVDA', 'AVGO'] },
    { title: 'Quiet Accumulation', tickers: ['COST', 'MSFT'] },
    { title: 'Earnings Catalyst Ahead', tickers: ['TSLA', 'AMD'] },
  ], [])

  async function addSymbol(symbol: string) {
    setErr('')
    setNotice('')
    setAdding(symbol)
    try {
      let target = selected
      if (!target) {
        target = await api.createWatchlist({ name: 'My Watchlist', category: 'Core', symbols: [symbol] })
        setLists((prev) => [target!, ...prev.filter((l) => l.id !== target!.id)])
        setListId(target.id)
      } else {
        const updated = await api.addStock(target.id, symbol)
        setLists((prev) => prev.map((l) => (l.id === updated.id ? updated : l)))
      }
      setNotice(`${symbol} added to ${target.name}.`)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setAdding(null)
    }
  }

  return (
    <div>
      <h1 className="text-[30px] font-semibold">Discover Stocks & Anomalies</h1>
      <p className="mt-1 text-sm text-[#94A3B8]">
        Type a company the way you say it — “Google”, “NVIDIA”, “Tesla” — or a ticker like GOOGL. Use the Add button on the right of any result.
      </p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search Google, NVIDIA, Apple…" /></div>
        {lists.length > 0 ? (
          <label className="text-sm text-[#94A3B8]">
            Watchlist
            <select
              className="ml-2 h-10 rounded border border-[#232F46] bg-[#0B0F17] px-2 text-on-surface"
              value={listId}
              onChange={(e) => setListId(Number(e.target.value))}
            >
              {lists.map((l) => (
                <option key={l.id} value={l.id}>{l.name}</option>
              ))}
            </select>
          </label>
        ) : (
          <p className="text-xs text-[#94A3B8]">First add creates “My Watchlist”.</p>
        )}
      </div>
      {notice ? <p className="mt-3 text-sm text-gain">{notice}</p> : null}
      {err ? <div className="mt-4"><ErrorState message={err} /></div> : null}
      {loading ? <p className="mt-4 text-sm text-[#94A3B8]">Searching…</p> : null}
      {!loading && q && hits.length === 0 ? <p className="mt-4 text-sm text-[#94A3B8]">No results for that query. Try the company name or the ticker.</p> : null}
      <div className="mt-4 grid gap-3">
        {hits.map((h) => (
          <Card key={h.symbol} className="relative flex flex-wrap items-center justify-between gap-3 pr-4">
            <div>
              <Link to={`/app/stocks/${h.symbol}`} className="font-mono text-lg">{h.symbol}</Link>
              <p className="text-sm text-[#94A3B8]">{h.company_name}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono">{h.current_price != null ? fmtPrice(h.current_price) : '—'}</span>
              <Delta value={h.price_change_percent} />
              <span className="text-xs text-[#94A3B8]">{h.data_status}</span>
              <Button
                className="shrink-0"
                variant="outline"
                disabled={adding === h.symbol}
                onClick={() => addSymbol(h.symbol)}
              >
                {adding === h.symbol ? 'Adding…' : 'Add'}
              </Button>
            </div>
          </Card>
        ))}
      </div>
      <h2 className="mt-10 text-lg font-semibold">Curated algorithmic clusters</h2>
      <div className="mt-3 grid gap-4 md:grid-cols-3">
        {clusters.map((c) => (
          <Card key={c.title}>
            <h3 className="font-semibold">{c.title}</h3>
            <p className="mt-2 font-mono text-sm text-primary">{c.tickers.join(' · ')}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {c.tickers.map((t) => (
                <Button key={t} variant="outline" onClick={() => addSymbol(t)}>Add {t}</Button>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
