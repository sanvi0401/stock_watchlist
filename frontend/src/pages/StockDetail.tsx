import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../services/api'
import type { Quote, Watchlist } from '../types'
import { Button, Card, DataBadge, Delta, ErrorState, SeverityPill, Skeleton, fmtCap, fmtPrice } from '../components/ui'

export default function StockDetailPage() {
  const { symbol } = useParams()
  const [q, setQ] = useState<Quote | null>(null)
  const [err, setErr] = useState('')
  const [range, setRange] = useState('Since Last Check')
  const [lists, setLists] = useState<Watchlist[]>([])
  const [added, setAdded] = useState('')
  useEffect(() => {
    if (!symbol) return
    api.stock(symbol).then(setQ).catch((e) => setErr(e.message || 'Stock not found'))
    api.watchlists().then(setLists).catch(() => undefined)
  }, [symbol])
  if (err) return <ErrorState message={err} />
  if (!q) return <Skeleton className="h-96" />
  const data = Array.from({ length: 12 }).map((_, i) => ({
    t: i,
    p: q.previous_price ? q.previous_price + ((q.current_price - q.previous_price) * i) / 11 : q.current_price,
  }))
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-sm text-[#94A3B8]">{q.symbol}</p>
          <h1 className="text-[30px] font-semibold">{q.company_name}</h1>
          <div className="mt-2 flex items-center gap-3">
            <span className="font-mono text-3xl">{fmtPrice(q.current_price)}</span>
            <Delta value={q.price_change_percent} />
            <DataBadge status={q.data_status} />
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <SeverityPill severity={q.severity} />
          <Button
            variant="outline"
            onClick={async () => {
              try {
                let list = lists[0]
                if (!list) {
                  list = await api.createWatchlist({ name: 'My Watchlist', symbols: [q.symbol] })
                  setLists([list])
                } else {
                  await api.addStock(list.id, q.symbol)
                }
                setAdded(`Added ${q.symbol} to ${list.name}`)
              } catch (e) {
                setErr((e as Error).message)
              }
            }}
          >
            Add to watchlist
          </Button>
          {added ? <p className="text-xs text-gain">{added}</p> : null}
        </div>
      </div>
      <Card>
        <div className="mb-3 flex flex-wrap gap-2">
          {['Since Last Check', '1D', '5D', '1M', '1Y'].map((r) => (
            <button key={r} onClick={() => setRange(r)} className={`rounded px-2 py-1 text-xs ${range === r ? 'bg-intel text-white' : 'text-[#94A3B8]'}`}>{r}</button>
          ))}
        </div>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid stroke="#232F46" />
              <XAxis dataKey="t" hide />
              <YAxis domain={['auto', 'auto']} stroke="#94A3B8" width={60} />
              <Tooltip contentStyle={{ background: '#1A2234', border: '1px solid #2E3E5B' }} />
              <Line type="monotone" dataKey="p" stroke="#6366F1" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-[#94A3B8]">{q.source} · {new Date(q.timestamp).toLocaleString()} · {q.market_state === 'CLOSED' ? 'Market closed' : 'Session open'}</p>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card accent="#6366F1">
          <h2 className="text-[11px] uppercase tracking-wider text-[#94A3B8]">What changed since you last checked?</h2>
          <p className="mt-2 font-mono text-2xl"><Delta value={q.since_last_check_percent} /></p>
          <p className="mt-2 text-sm text-[#CBD5E1]">{q.first_seen ? q.explanation : q.explanation}</p>
        </Card>
        <Card>
          <h2 className="text-[11px] uppercase tracking-wider text-[#94A3B8]">Why this matters</h2>
          <p className="mt-2 text-sm">{q.explanation}</p>
          <ul className="mt-3 list-disc pl-5 text-sm text-[#94A3B8]">
            {q.evidence.map((e) => <li key={e}>{e}</li>)}
          </ul>
        </Card>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ['Previous close', fmtPrice(q.previous_close)],
          ['Volume', q.volume.toLocaleString()],
          ['Avg volume', q.average_volume.toLocaleString()],
          ['Volatility', `${(q.volatility * 100).toFixed(1)}%`],
          ['Market cap', fmtCap(q.market_cap)],
          ['52w high', fmtPrice(q.week_52_high)],
          ['52w low', fmtPrice(q.week_52_low)],
          ['Score', `${q.significance_score}/100`],
        ].map(([k, v]) => (
          <Card key={k}><p className="text-[11px] uppercase tracking-wider text-[#94A3B8]">{k}</p><p className="mt-1 font-mono">{v}</p></Card>
        ))}
      </div>
      <Link to="/app/history" className="text-sm text-primary">Open change history</Link>
    </div>
  )
}
