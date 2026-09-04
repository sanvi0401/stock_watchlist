import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../services/api'
import type { HistoryItem } from '../types'
import { Button, Card, Delta, ErrorState, SeverityPill, Skeleton } from '../components/ui'
import { fmtDateTime, fmtPrice } from '../utils/format'

const FILTERS = ['All', 'HIGH', 'MEANINGFUL', 'NOTABLE'] as const
const LABEL: Record<string, string> = { All: 'All', HIGH: 'High significance', MEANINGFUL: 'Meaningful', NOTABLE: 'Notable' }
const ACCENT: Record<string, string> = { HIGH: '#F43F5E', MEANINGFUL: '#F59E0B', NOTABLE: '#6366F1', STABLE: '#10B981' }

export default function HistoryPage() {
  const [params] = useSearchParams()
  const symbol = params.get('symbol') || undefined
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('All')
  const key = `${filter}|${symbol ?? ''}`
  const [page, setPage] = useState<{ key: string; items: HistoryItem[]; cursor: number | null }>({ key: '', items: [], cursor: null })
  const [more, setMore] = useState(false)
  const [err, setErr] = useState('')
  const loading = page.key !== key || more
  const items = page.key === key ? page.items : []
  const cursor = page.key === key ? page.cursor : null
  const severity = filter === 'All' ? undefined : filter

  useEffect(() => {
    let cancelled = false
    api.history({ severity, symbol })
      .then((res) => { if (!cancelled) { setPage({ key, items: res.items, cursor: res.next_cursor }); setErr('') } })
      .catch((e) => { if (!cancelled) { setPage({ key, items: [], cursor: null }); setErr((e as Error).message) } })
    return () => { cancelled = true }
  }, [key, severity, symbol])

  const loadMore = useCallback(async () => {
    if (!cursor) return
    setMore(true)
    try {
      const res = await api.history({ severity, symbol, cursor })
      setPage((prev) => ({ key, items: [...prev.items, ...res.items], cursor: res.next_cursor }))
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setMore(false)
    }
  }, [cursor, key, severity, symbol])

  return (
    <div>
      <h1 className="text-[30px] font-semibold">Change history{symbol ? ` · ${symbol}` : ''}</h1>
      <p className="mt-1 text-sm text-[#94A3B8]">One entry per visit per symbol, written only when a move cleared the notable threshold. Refreshing never duplicates it.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3 py-1 text-xs ${filter === f ? 'border-intel text-primary' : 'border-[#232F46] text-[#94A3B8]'}`}
          >
            {LABEL[f]}
          </button>
        ))}
        {symbol ? <Link to="/app/history" className="self-center text-xs text-primary">Clear symbol filter</Link> : null}
      </div>
      {err ? <div className="mt-4"><ErrorState message={err} /></div> : null}
      <div className="mt-6 space-y-3">
        {items.map((it) => (
          <Card key={it.id} accent={ACCENT[it.severity]}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link to={`/app/stocks/${it.symbol}`} className="font-mono text-lg">{it.symbol}</Link>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-[#94A3B8]">{fmtPrice(it.baseline_price, it.currency)} → {fmtPrice(it.current_price, it.currency)}</span>
                <Delta value={it.since_last_check_percent} />
                <SeverityPill severity={it.severity} />
              </div>
            </div>
            <p className="mt-2 text-sm text-[#CBD5E1]">{it.explanation}</p>
            <p className="mt-2 text-xs text-[#94A3B8]">{fmtDateTime(it.timestamp)} · score {it.significance_score}</p>
          </Card>
        ))}
        {loading ? <Skeleton className="h-24" /> : null}
        {!loading && items.length === 0 && !err ? (
          <p className="text-sm text-[#94A3B8]">Nothing recorded yet. Changes are logged when you open Overview and something has moved meaningfully since your previous visit.</p>
        ) : null}
        {cursor && !loading ? <Button variant="outline" onClick={loadMore}>Load older</Button> : null}
      </div>
    </div>
  )
}
