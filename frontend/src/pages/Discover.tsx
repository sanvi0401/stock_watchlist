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
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  useEffect(() => { api.watchlists().then(setLists).catch(() => undefined) }, [])
  useEffect(() => {
    const t = setTimeout(() => {
      if (!q.trim()) { setHits([]); return }
      setLoading(true)
      api.search(q.trim()).then(setHits).catch((e) => setErr(e.message)).finally(() => setLoading(false))
    }, 280)
    return () => clearTimeout(t)
  }, [q])
  const firstList = lists[0]
  const clusters = useMemo(() => [
    { title: 'Unusual Institutional Flow', tickers: ['NVDA', 'AVGO'] },
    { title: 'Quiet Accumulation', tickers: ['COST', 'MSFT'] },
    { title: 'Earnings Catalyst Ahead', tickers: ['TSLA', 'AMD'] },
  ], [])
  return (
    <div>
      <h1 className="text-[30px] font-semibold">Discover Stocks & Anomalies</h1>
      <p className="mt-1 text-sm text-[#94A3B8]">Search by company or ticker. This is not a generic screener — results are for adding names you intend to monitor.</p>
      <div className="mt-4"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search companies, ticker symbols, or anomaly catalysts..." /></div>
      {err ? <div className="mt-4"><ErrorState message={err} /></div> : null}
      {loading ? <p className="mt-4 text-sm text-[#94A3B8]">Searching…</p> : null}
      {!loading && q && hits.length === 0 ? <p className="mt-4 text-sm text-[#94A3B8]">No results for that query.</p> : null}
      <div className="mt-4 grid gap-3">
        {hits.map((h) => (
          <Card key={h.symbol} className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <Link to={`/app/stocks/${h.symbol}`} className="font-mono text-lg">{h.symbol}</Link>
              <p className="text-sm text-[#94A3B8]">{h.company_name}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono">{h.current_price != null ? fmtPrice(h.current_price) : '—'}</span>
              <Delta value={h.price_change_percent} />
              <span className="text-xs text-[#94A3B8]">{h.data_status}</span>
              {firstList ? (
                <Button variant="outline" onClick={() => api.addStock(firstList.id, h.symbol).catch((e) => setErr(e.message))}>Add to Watchlist</Button>
              ) : null}
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
          </Card>
        ))}
      </div>
    </div>
  )
}
