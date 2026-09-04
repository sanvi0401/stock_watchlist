import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { HistoryItem } from '../types'
import { Button, Card, SeverityPill, Skeleton } from '../components/ui'

const filters = ['All', 'HIGH', 'MEANINGFUL', 'NOTABLE', 'STABLE']

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [cursor, setCursor] = useState<number | null>(null)
  const [filter, setFilter] = useState('All')
  const [loading, setLoading] = useState(true)

  async function load(reset = false) {
    setLoading(true)
    const page = await api.history(filter === 'All' ? undefined : filter, reset ? undefined : cursor || undefined)
    setItems((prev) => (reset ? page.items : [...prev, ...page.items]))
    setCursor(page.next_cursor)
    setLoading(false)
  }
  useEffect(() => { load(true) }, [filter])

  return (
    <div>
      <h1 className="text-[30px] font-semibold">Change History & Activity Timeline</h1>
      <div className="mt-4 flex flex-wrap gap-2">
        {filters.map((f) => (
          <button key={f} onClick={() => { setFilter(f); setCursor(null) }} className={`rounded-full border px-3 py-1 text-xs ${filter === f ? 'border-intel text-primary' : 'border-[#232F46] text-[#94A3B8]'}`}>{f === 'HIGH' ? 'High Significance' : f}</button>
        ))}
      </div>
      <div className="mt-6 space-y-3">
        {items.map((it) => (
          <Card key={it.id} accent={it.severity === 'HIGH' ? '#F43F5E' : '#6366F1'}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link to={`/app/stocks/${it.symbol}`} className="font-mono text-lg">{it.symbol}</Link>
              <SeverityPill severity={it.severity} />
            </div>
            <p className="mt-2 text-sm text-[#CBD5E1]">{it.explanation}</p>
            <p className="mt-2 text-xs text-[#94A3B8]">{new Date(it.timestamp).toLocaleString()} · {it.change_type} · {it.significance_score}</p>
          </Card>
        ))}
        {loading ? <Skeleton className="h-24" /> : null}
        {!loading && items.length === 0 ? <p className="text-sm text-[#94A3B8]">No persisted changes yet. Open Overview to run a last-seen comparison.</p> : null}
        {cursor ? <Button variant="outline" onClick={() => load(false)}>Load older ledger entries</Button> : null}
      </div>
    </div>
  )
}
