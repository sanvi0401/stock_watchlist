import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../services/api'
import type { Quote, Watchlist } from '../types'
import { Button, Card, DataBadge, Delta, ErrorState, ExchangeTag, SeverityPill, Skeleton } from '../components/ui'
import { MARKET_LABEL, fmtCap, fmtDateTime, fmtPrice, fmtRelative, fmtVolume } from '../utils/format'

export default function StockDetailPage() {
  const { symbol } = useParams()
  const [q, setQ] = useState<Quote | null>(null)
  const [err, setErr] = useState('')
  const [lists, setLists] = useState<Watchlist[]>([])
  const [listId, setListId] = useState<number | ''>('')
  const [notice, setNotice] = useState('')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    if (!symbol) return
    api.stock(symbol).then(setQ).catch((e) => setErr(e.message || 'Stock not found'))
    api.watchlists().then((rows) => {
      setLists(rows)
      if (rows[0]) setListId(rows[0].id)
    }).catch(() => undefined)
  }, [symbol])

  if (err) return <ErrorState message={err} />
  if (!q) return <Skeleton className="h-96" />

  const series = q.sparkline.map((p, i) => ({ i, p }))
  const inList = lists.some((l) => l.id === listId && l.stocks.some((s) => s.symbol === q.symbol))

  async function add() {
    setAdding(true)
    setNotice('')
    try {
      if (!listId) {
        const created = await api.createWatchlist({ name: 'My Watchlist', category: 'Core', symbols: [q!.symbol] })
        setLists([created])
        setListId(created.id)
        setNotice(`Created "My Watchlist" with ${q!.symbol}.`)
      } else {
        const updated = await api.addStock(listId, q!.symbol)
        setLists((prev) => prev.map((l) => (l.id === updated.id ? updated : l)))
        setNotice(`Added ${q!.symbol} to ${updated.name}.`)
      }
    } catch (e) {
      setNotice((e as Error).message)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 font-mono text-sm text-[#94A3B8]">{q.symbol} <ExchangeTag name={q.exchange_name} state={q.market_state} /></p>
          <h1 className="text-[30px] font-semibold">{q.company_name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <span className="font-mono text-3xl">{fmtPrice(q.current_price, q.currency)}</span>
            <span className="text-xs text-[#94A3B8]">today</span>
            <Delta value={q.price_change_percent} />
            <DataBadge status={q.data_status} />
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <SeverityPill severity={q.severity} />
          <div className="flex items-center gap-2">
            {lists.length > 0 ? (
              <select
                className="h-9 rounded border border-[#232F46] bg-[#0B0F17] px-2 text-sm"
                value={listId}
                onChange={(e) => setListId(Number(e.target.value))}
                aria-label="Watchlist"
              >
                {lists.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            ) : null}
            <Button variant="outline" onClick={add} disabled={adding || inList}>
              {inList ? 'On this list' : adding ? 'Adding…' : 'Add to watchlist'}
            </Button>
          </div>
          {notice ? <p className="text-xs text-gain">{notice}</p> : null}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card accent="#6366F1">
          <h2 className="text-[11px] uppercase tracking-wider text-[#94A3B8]">Since you last checked</h2>
          <div className="mt-2 flex items-center gap-3">
            <span className="font-mono text-2xl">{q.first_seen ? '—' : <Delta value={q.since_last_check_percent} />}</span>
            {q.previous_price != null && !q.first_seen ? (
              <span className="text-sm text-[#94A3B8]">from {fmtPrice(q.previous_price, q.currency)} {q.baseline_at ? `(${fmtRelative(q.baseline_at)})` : ''}</span>
            ) : null}
          </div>
          <p className="mt-2 text-sm text-[#CBD5E1]">{q.explanation}</p>
          <p className="mt-2 text-[11px] text-[#94A3B8]">Viewing this page does not move your baseline. Only the Overview counts as a check.</p>
        </Card>
        <Card>
          <h2 className="text-[11px] uppercase tracking-wider text-[#94A3B8]">Why this matters · score {q.significance_score}/100</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[#CBD5E1]">
            {q.evidence.map((e) => <li key={e}>{e}</li>)}
          </ul>
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[11px] uppercase tracking-wider text-[#94A3B8]">Recent closes · last {series.length} sessions</h2>
          <p className="text-xs text-[#94A3B8]">{q.source} · {fmtDateTime(q.timestamp)} · {q.exchange_name} {MARKET_LABEL[q.market_state] ?? q.market_state}</p>
        </div>
        {series.length < 2 ? (
          <p className="mt-4 text-sm text-[#94A3B8]">This provider does not return price history for {q.symbol}.</p>
        ) : (
          <div className="mt-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series}>
                <CartesianGrid stroke="#232F46" />
                <XAxis dataKey="i" hide />
                <YAxis domain={['auto', 'auto']} stroke="#94A3B8" width={72} tickFormatter={(v: number) => v.toFixed(v < 10 ? 2 : 0)} />
                <Tooltip
                  contentStyle={{ background: '#1A2234', border: '1px solid #2E3E5B' }}
                  formatter={(v) => [fmtPrice(Number(v), q.currency), 'Close']}
                  labelFormatter={(i) => `${series.length - Number(i) - 1} session(s) ago`}
                />
                {q.previous_price != null && !q.first_seen ? (
                  <ReferenceLine y={q.previous_price} stroke="#F59E0B" strokeDasharray="4 4" label={{ value: 'you last saw', fill: '#F59E0B', fontSize: 11, position: 'insideTopLeft' }} />
                ) : null}
                <Line type="monotone" dataKey="p" stroke="#6366F1" dot={false} strokeWidth={2} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ['Previous close', fmtPrice(q.previous_close, q.currency)],
          ['Volume', fmtVolume(q.volume)],
          ['Avg volume (60d)', fmtVolume(q.average_volume)],
          ['Typical daily move', `${(q.volatility * 100).toFixed(1)}%`],
          ['Market cap', fmtCap(q.market_cap, q.currency)],
          ['52w high', fmtPrice(q.week_52_high, q.currency)],
          ['52w low', fmtPrice(q.week_52_low, q.currency)],
          ['Exchange', `${q.exchange_name || q.exchange} · ${q.currency}`],
        ].map(([k, v]) => (
          <Card key={k}><p className="text-[11px] uppercase tracking-wider text-[#94A3B8]">{k}</p><p className="mt-1 font-mono">{v}</p></Card>
        ))}
      </div>
      <Link to={`/app/history?symbol=${q.symbol}`} className="text-sm text-primary">Change history for {q.symbol} →</Link>
    </div>
  )
}
