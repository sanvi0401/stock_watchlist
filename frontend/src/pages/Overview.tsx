import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { Dashboard, Quote } from '../types'
import { Button, Card, DataBadge, Delta, EmptyState, ErrorState, SeverityPill, Skeleton, fmtPrice } from '../components/ui'

function QuoteCard({ q }: { q: Quote }) {
  return (
    <Card accent={q.severity === 'HIGH' ? '#F43F5E' : q.severity === 'MEANINGFUL' ? '#F59E0B' : '#6366F1'}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to={`/app/stocks/${q.symbol}`} className="font-mono text-lg font-medium">{q.symbol}</Link>
          <p className="text-sm text-[#94A3B8]">{q.company_name}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-xl">{fmtPrice(q.current_price)}</p>
          <Delta value={q.since_last_check_percent ?? q.price_change_percent} />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <SeverityPill severity={q.severity} />
        <DataBadge status={q.data_status} />
        <span className="font-mono text-xs text-[#94A3B8]">{q.significance_score}/100</span>
      </div>
      <p className="mt-3 text-sm text-[#CBD5E1]">{q.explanation}</p>
      <Link to={`/app/stocks/${q.symbol}`} className="mt-3 inline-block text-sm text-primary">View why & full analysis →</Link>
    </Card>
  )
}

export default function OverviewPage() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.dashboard().then(setData).catch((e) => setErr(e.message))
  }, [])
  if (err) return <ErrorState message={err} />
  if (!data) {
    return <div className="grid gap-4 md:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-40" />)}</div>
  }
  if (data.stocks_tracked === 0) {
    return <EmptyState title="Empty watchlist" body="Add names so we can remember a baseline and detect what changed since you last checked." action={<Link to="/app/watchlists"><Button>Create a watchlist</Button></Link>} />
  }
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[30px] font-semibold leading-[38px]">{data.greeting}</h1>
        <p className="mt-1 text-sm text-[#94A3B8]">
          {data.first_time ? 'First check: baselines recorded. Come back later to see what meaningfully changed.' : `Last checked ${data.last_checked_at ? new Date(data.last_checked_at).toLocaleString() : '—'}`}
          {' · '}
          {data.market_state === 'CLOSED' ? 'Market closed' : 'US session'}
          {' · '}
          <DataBadge status={data.data_status} />
        </p>
      </div>
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
          <p className="text-sm text-[#94A3B8]">Nothing at high significance right now.</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">{data.needs_attention_items.map((q) => <QuoteCard key={q.symbol} q={q} />)}</div>
        )}
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Meaningful changes</h2>
        {data.meaningful_items.length === 0 ? (
          <p className="text-sm text-[#94A3B8]">No notable or meaningful moves since last check.</p>
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
                <tr>{['Symbol & entity', 'Price', 'Since check', 'Today', 'Status'].map((h) => <th key={h} className="px-3 py-2 font-semibold">{h}</th>)}</tr>
              </thead>
              <tbody>
                {data.stable_items.map((q) => (
                  <tr key={q.symbol} className="border-t border-[#232F46] hover:bg-[#1A2234]">
                    <td className="px-3 py-3"><Link to={`/app/stocks/${q.symbol}`} className="font-mono">{q.symbol}</Link> <span className="text-[#94A3B8]">{q.company_name}</span></td>
                    <td className="px-3 py-3 text-right font-mono">{fmtPrice(q.current_price)}</td>
                    <td className="px-3 py-3 text-right"><Delta value={q.since_last_check_percent} /></td>
                    <td className="px-3 py-3 text-right"><Delta value={q.price_change_percent} /></td>
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
          {data.unavailable_items.map((q) => <Card key={q.symbol} accent="#F43F5E" className="mb-2"><p className="font-mono">{q.symbol}</p><p className="text-sm">{q.explanation}</p></Card>)}
        </section>
      ) : null}
    </div>
  )
}
