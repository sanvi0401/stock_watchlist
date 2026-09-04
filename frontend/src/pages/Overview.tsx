import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { Dashboard, Quote } from '../types'
import { Button, Card, DataBadge, Delta, EmptyState, ErrorState, ExchangeTag, SeverityPill, Skeleton } from '../components/ui'
import { fmtPrice, fmtRelative, marketLine } from '../utils/format'

const ACCENT: Record<string, string> = { HIGH: '#F43F5E', MEANINGFUL: '#F59E0B', NOTABLE: '#6366F1', STABLE: '#10B981' }

function QuoteCard({ q }: { q: Quote }) {
  return (
    <Card accent={ACCENT[q.severity]}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to={`/app/stocks/${q.symbol}`} className="font-mono text-lg font-medium">{q.symbol}</Link>
          <ExchangeTag name={q.exchange_name} state={q.market_state} />
          <p className="text-sm text-[#94A3B8]">{q.company_name}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-xl">{fmtPrice(q.current_price, q.currency)}</p>
          <Delta value={q.since_last_check_percent} />
          <p className="mt-1 text-[11px] text-[#94A3B8]">since {fmtRelative(q.baseline_at)}</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <SeverityPill severity={q.severity} />
        <DataBadge status={q.data_status} />
        <span className="font-mono text-xs text-[#94A3B8]">score {q.significance_score}/100</span>
      </div>
      <p className="mt-3 text-sm text-[#CBD5E1]">{q.explanation}</p>
      <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-[#94A3B8]">
        {q.evidence.slice(0, 3).map((e) => <li key={e}>{e}</li>)}
      </ul>
      <Link to={`/app/stocks/${q.symbol}`} className="mt-3 inline-block text-sm text-primary">Open full briefing →</Link>
    </Card>
  )
}

export default function OverviewPage() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  const load = useCallback(() => api.dashboard().then(setData).catch((e) => setErr(e.message)), [])
  useEffect(() => {
    void load()
  }, [load])

  async function markSeen() {
    setBusy(true)
    setNotice('')
    try {
      const r = await api.checkpoint()
      setNotice(`Baseline reset for ${r.symbols} symbol${r.symbols === 1 ? '' : 's'}. Next visit compares against right now.`)
      await load()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (err) return <ErrorState message={err} />
  if (!data) {
    return <div className="grid gap-4 md:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-40" />)}</div>
  }
  if (data.stocks_tracked === 0) {
    return (
      <EmptyState
        title="Nothing tracked yet"
        body="Add a few names. We record the price you saw, then tell you what moved meaningfully when you come back."
        action={<Link to="/app/watchlists"><Button>Create a watchlist</Button></Link>}
      />
    )
  }

  const subtitle = data.first_time
    ? 'First check: baselines recorded. Come back later and this page will show only what changed.'
    : `Comparing against what you saw ${fmtRelative(data.baseline_at)}${data.new_visit ? ' · new visit' : ''}`

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[30px] font-semibold leading-[38px]">{data.greeting}</h1>
          <p className="mt-1 text-sm text-[#94A3B8]">
            {subtitle}
            {data.markets.length ? ` · ${marketLine(data.markets)}` : ''}
            {' · '}
            <DataBadge status={data.data_status} />
          </p>
        </div>
        <div className="text-right">
          <Button variant="outline" onClick={markSeen} disabled={busy}>{busy ? 'Resetting…' : "I'm caught up"}</Button>
          <p className="mt-1 max-w-xs text-[11px] text-[#94A3B8]">Resets every baseline to the current price.</p>
        </div>
      </div>
      {notice ? <p className="text-sm text-gain">{notice}</p> : null}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ['Stocks tracked', String(data.stocks_tracked)],
          ['Needs attention', String(data.needs_attention)],
          ['Meaningful changes', String(data.meaningful_changes)],
          ['Stable', String(data.stable_count)],
        ].map(([k, v]) => (
          <Card key={k}><p className="text-[11px] uppercase tracking-wider text-[#94A3B8]">{k}</p><p className="mt-1 font-mono text-2xl">{v}</p></Card>
        ))}
      </div>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Needs your attention</h2>
        {data.needs_attention_items.length === 0 ? (
          <p className="text-sm text-[#94A3B8]">Nothing unusual for these names since you last looked.</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">{data.needs_attention_items.map((q) => <QuoteCard key={q.symbol} q={q} />)}</div>
        )}
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Meaningful changes</h2>
        {data.meaningful_items.length === 0 ? (
          <p className="text-sm text-[#94A3B8]">No notable or meaningful moves since your last check.</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">{data.meaningful_items.map((q) => <QuoteCard key={q.symbol} q={q} />)}</div>
        )}
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold text-[#94A3B8]">No significant change</h2>
        {data.stable_items.length === 0 ? (
          <p className="text-sm text-[#94A3B8]">—</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-[#232F46]">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-[#94A3B8]">
                <tr>{['Symbol', 'Price', 'Since check', 'Today', 'Feed', 'Status'].map((h) => <th key={h} className="px-3 py-2 font-semibold">{h}</th>)}</tr>
              </thead>
              <tbody>
                {data.stable_items.map((q) => (
                  <tr key={q.symbol} className="border-t border-[#232F46] hover:bg-[#1A2234]">
                    <td className="px-3 py-3"><Link to={`/app/stocks/${q.symbol}`} className="font-mono">{q.symbol}</Link> <ExchangeTag name={q.exchange_name} state={q.market_state} /> <span className="text-[#94A3B8]">{q.company_name}</span></td>
                    <td className="px-3 py-3 font-mono">{fmtPrice(q.current_price, q.currency)}</td>
                    <td className="px-3 py-3">{q.first_seen ? <span className="text-xs text-[#94A3B8]">baseline set</span> : <Delta value={q.since_last_check_percent} />}</td>
                    <td className="px-3 py-3"><Delta value={q.price_change_percent} /></td>
                    <td className="px-3 py-3"><DataBadge status={q.data_status} /></td>
                    <td className="px-3 py-3"><SeverityPill severity={q.severity} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {data.unavailable_items.length > 0 ? (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-loss">Unavailable</h2>
          {data.unavailable_items.map((q) => (
            <Card key={q.symbol} accent="#F43F5E" className="mb-2">
              <p className="font-mono">{q.symbol}</p>
              <p className="text-sm text-[#CBD5E1]">{q.explanation}</p>
              {q.current_price > 0 ? <p className="mt-1 text-xs text-[#94A3B8]">Last valid price you saw: {fmtPrice(q.current_price, q.currency)}</p> : null}
            </Card>
          ))}
        </section>
      ) : null}
    </div>
  )
}
