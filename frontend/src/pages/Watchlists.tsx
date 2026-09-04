import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Watchlist } from '../types'
import { Button, Card, EmptyState, ErrorState, Input, Label, Modal, Skeleton } from '../components/ui'

export default function WatchlistsPage() {
  const [rows, setRows] = useState<Watchlist[] | null>(null)
  const [err, setErr] = useState('')
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  useEffect(() => { api.watchlists().then(setRows).catch((e) => setErr(e.message)) }, [])

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    try {
      const wl = await api.createWatchlist({
        name: String(fd.get('name')),
        category: String(fd.get('category') || 'General'),
        symbols: String(fd.get('symbols') || '').split(',').map((s) => s.trim()).filter(Boolean),
      })
      setOpen(false)
      nav(`/app/watchlists/${wl.id}`)
    } catch (ex) {
      setErr((ex as Error).message)
    }
  }

  if (err) return <ErrorState message={err} />
  if (!rows) return <Skeleton className="h-64" />
  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-[30px] font-semibold">My Watchlists</h1>
        <Button onClick={() => setOpen(true)}>+ Create New Watchlist</Button>
      </div>
      {rows.length === 0 ? (
        <EmptyState title="No watchlists yet" body="Create a list. Every name you add gets a baseline so the next visit can show what changed." action={<Button onClick={() => setOpen(true)}>Create watchlist</Button>} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {rows.map((w) => (
            <Card key={w.id}>
              <p className="text-[11px] uppercase tracking-wider text-[#94A3B8]">{w.category}</p>
              <h2 className="text-xl font-semibold">{w.name}</h2>
              <p className="mt-1 text-sm text-[#94A3B8]">{w.stock_count} names · {w.attention_count} need attention · {w.meaningful_count} meaningful{w.unavailable_count ? ` · ${w.unavailable_count} unavailable` : ''}</p>
              <div className="mt-4 flex gap-2">
                <Link to={`/app/watchlists/${w.id}`}><Button>Open Watchlist</Button></Link>
              </div>
            </Card>
          ))}
        </div>
      )}
      <Modal open={open} title="New watchlist" onClose={() => setOpen(false)}>
        <form className="space-y-3" onSubmit={create}>
          <div><Label>Name</Label><Input name="name" required /></div>
          <div><Label>Category</Label><Input name="category" placeholder="Tech" /></div>
          <div><Label>Symbols or company names (optional)</Label><Input name="symbols" placeholder="NVDA, AAPL" /></div>
          <Button type="submit">Create</Button>
        </form>
      </Modal>
    </div>
  )
}
