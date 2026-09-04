import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'

export function SettingsPage() {
  const [form, setForm] = useState<Record<string, string | boolean>>({})
  useEffect(() => {
    api.settings().then((s) => setForm(s as Record<string, string | boolean>))
  }, [])
  async function save(e: FormEvent) {
    e.preventDefault()
    await api.patchSettings(form)
  }
  return (
    <form className="max-w-3xl space-y-6" onSubmit={save}>
      <h1 className="text-[30px] font-semibold">System Settings & Intelligence Controls</h1>
      <Card>
        <h2 className="mb-3 font-semibold">Personal & analytical locale</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <div><Label>Full name</Label><Input value={String(form.name || '')} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          <div><Label>Work email</Label><Input value={String(form.email || '')} disabled /></div>
          <div><Label>Timezone</Label><Input value={String(form.timezone || '')} onChange={(e) => setForm({ ...form, timezone: e.target.value })} /></div>
          <div><Label>Valuation currency</Label><Input value={String(form.currency || '')} onChange={(e) => setForm({ ...form, currency: e.target.value })} /></div>
        </div>
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">Anomaly detection sensitivity</h2>
        {['conservative', 'balanced', 'sensitive'].map((s) => (
          <label key={s} className="mb-2 flex items-center gap-2 text-sm">
            <input type="radio" checked={form.sensitivity === s} onChange={() => setForm({ ...form, sensitivity: s })} /> {s}
          </label>
        ))}
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">Notification protocols</h2>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!form.email_alerts} onChange={(e) => setForm({ ...form, email_alerts: e.target.checked })} /> Email</label>
        <label className="mt-2 flex items-center gap-2 text-sm"><input type="checkbox" checked={!!form.push_alerts} onChange={(e) => setForm({ ...form, push_alerts: e.target.checked })} /> Mobile push</label>
      </Card>
      <div className="flex gap-3">
        <Button type="submit">Save changes</Button>
        <Link to="/app/profile" className="text-sm text-primary self-center">Profile</Link>
        <Link to="/app/preferences" className="text-sm text-primary self-center">Preferences</Link>
      </div>
    </form>
  )
}

export function ProfilePage() {
  const [me, setMe] = useState<{ name: string; email: string } | null>(null)
  useEffect(() => { api.me().then((u) => setMe(u as { name: string; email: string })) }, [])
  return (
    <Card className="max-w-xl">
      <h1 className="text-2xl font-semibold">Profile</h1>
      <p className="mt-4">{me?.name}</p>
      <p className="text-[#94A3B8]">{me?.email}</p>
    </Card>
  )
}

export function PreferencesPage() {
  return (
    <Card className="max-w-xl">
      <h1 className="text-2xl font-semibold">Preferences</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">Lookback defaults to since last check. Adjust intelligence sensitivity in Settings.</p>
    </Card>
  )
}

export function NotificationsPage() {
  const [rows, setRows] = useState<Array<{ id: number; title: string; body: string; created_at: string; read: boolean }>>([])
  useEffect(() => { api.notifications().then(setRows) }, [])
  return (
    <div>
      <h1 className="text-[30px] font-semibold">Notifications</h1>
      <div className="mt-4 space-y-3">
        {rows.length === 0 ? <p className="text-sm text-[#94A3B8]">No dispatches yet.</p> : rows.map((n) => (
          <Card key={n.id}><p className="font-semibold">{n.title}</p><p className="text-sm text-[#CBD5E1]">{n.body}</p><p className="text-xs text-[#94A3B8]">{new Date(n.created_at).toLocaleString()}</p></Card>
        ))}
      </div>
    </div>
  )
}

export function NotFoundPage() {
  return <Card><h1 className="text-2xl font-semibold">404</h1><p className="mt-2 text-sm">That page is not in the terminal.</p></Card>
}

export function ErrorPage() {
  return <Card accent="#F43F5E"><h1 className="text-2xl font-semibold">Something went wrong</h1><p className="text-sm">A generic error was caught. Reload and try again.</p></Card>
}
