import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { api } from '../services/api'
import type { Notification, Settings } from '../types'
import { Button, Card, ErrorState, Input, Label } from '../components/ui'
import { LegalModal } from '../components/LegalModal'
import { fmtDateTime } from '../utils/format'
import { LOOKBACKS, SENSITIVITIES, TIMEZONES } from '../constants'

const EMPTY: Settings = {
  name: '',
  email: '',
  timezone: 'Asia/Kolkata',
  sensitivity: 'balanced',
  lookback_mode: 'since_last_check',
  high_significance_only: false,
  onboarding_complete: true,
}

export function Select({ value, onChange, children, label }: { value: string; onChange: (v: string) => void; children: ReactNode; label?: string }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
      className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm text-[#F8FAFC] outline-none focus:border-intel"
    >
      {children}
    </select>
  )
}

export function ChoiceCards({ name, value, options, onPick }: { name: string; value: string; options: { id: string; title: string; body: string }[]; onPick: (id: string) => void }) {
  return (
    <div className="grid gap-3">
      {options.map((opt) => {
        const on = value === opt.id
        return (
          <label key={opt.id} className={`flex cursor-pointer gap-3 rounded-lg border p-3 ${on ? 'border-intel bg-intel/10' : 'border-[#232F46] hover:border-[#2E3E5B]'}`}>
            <input type="radio" name={name} className="mt-1" checked={on} onChange={() => onPick(opt.id)} />
            <span>
              <span className="block font-medium">{opt.title}</span>
              <span className="mt-1 block text-sm text-[#94A3B8]">{opt.body}</span>
            </span>
          </label>
        )
      })}
    </div>
  )
}

export function SettingsPage() {
  const [form, setForm] = useState<Settings>(EMPTY)
  const [loaded, setLoaded] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)
  const [legal, setLegal] = useState<null | 'terms' | 'privacy'>(null)

  useEffect(() => {
    api.settings().then((s) => { setForm({ ...EMPTY, ...s }); setLoaded(true) }).catch((e) => setErr(e.message))
  }, [])

  async function persist(patch: Partial<Settings>, notice: string) {
    setSaving(true)
    setErr('')
    setMsg('')
    try {
      const saved = await api.patchSettings(patch)
      setForm({ ...EMPTY, ...saved })
      setMsg(notice)
    } catch (e) {
      setErr((e as Error).message || 'Could not save settings')
    } finally {
      setSaving(false)
    }
  }

  async function saveProfile(e: FormEvent) {
    e.preventDefault()
    await persist({ name: form.name, timezone: form.timezone }, 'Profile saved.')
  }

  if (err && !loaded) return <ErrorState message={err} />

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-[30px] font-semibold">Settings</h1>
      <form onSubmit={saveProfile}>
        <Card>
          <h2 className="mb-3 font-semibold">Profile</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
            <div><Label>Email</Label><Input value={form.email} disabled /></div>
            <div>
              <Label>Timezone</Label>
              <Select label="Timezone" value={form.timezone} onChange={(timezone) => setForm({ ...form, timezone })}>
                {TIMEZONES.map((z) => <option key={z} value={z}>{z.replace(/_/g, ' ')}</option>)}
              </Select>
              <p className="mt-1 text-xs text-[#94A3B8]">Used for greetings and timestamps. Market hours follow each stock’s own exchange.</p>
            </div>
            <div><Label>Member since</Label><p className="text-sm text-[#CBD5E1]">{fmtDateTime(form.created_at)}</p></div>
          </div>
          <Button className="mt-4" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</Button>
        </Card>
      </form>
      <Card>
        <h2 className="mb-1 font-semibold">Sensitivity</h2>
        <p className="mb-3 text-sm text-[#94A3B8]">How far outside a name’s own typical range a move must be before it is escalated. Applied on your next check.</p>
        <ChoiceCards name="sensitivity" value={form.sensitivity} options={SENSITIVITIES} onPick={(sensitivity) => void persist({ sensitivity }, `${sensitivity} mode is on.`)} />
      </Card>
      <Card>
        <h2 className="mb-1 font-semibold">Comparison baseline</h2>
        <p className="mb-3 text-sm text-[#94A3B8]">What “since last check” compares against.</p>
        <ChoiceCards name="lookback" value={form.lookback_mode} options={LOOKBACKS} onPick={(lookback_mode) => void persist({ lookback_mode }, 'Baseline updated.')} />
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">Overview</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.high_significance_only}
            onChange={(e) => void persist({ high_significance_only: e.target.checked }, e.target.checked ? 'Overview will only escalate HIGH moves.' : 'Overview will show meaningful and notable moves again.')}
          />
          Only escalate high-significance moves on Overview
        </label>
      </Card>
      {err ? <p className="text-sm text-loss">{err}</p> : null}
      {msg ? <p className="text-sm text-gain">{msg}</p> : null}
      <p className="text-sm text-[#94A3B8]">
        <button type="button" className="text-primary underline" onClick={() => setLegal('terms')}>Terms of Service</button>
        {' · '}
        <button type="button" className="text-primary underline" onClick={() => setLegal('privacy')}>Privacy Policy</button>
      </p>
      <LegalModal kind={legal} onClose={() => setLegal(null)} />
    </div>
  )
}

export function NotificationsPage() {
  const [rows, setRows] = useState<Notification[] | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.notifications()
      .then((list) => {
        setRows(list)
        if (list.some((n) => !n.read)) api.markNotificationsRead().catch(() => undefined)
      })
      .catch((e) => setErr(e.message))
  }, [])
  if (err) return <ErrorState message={err} />
  return (
    <div>
      <h1 className="text-[30px] font-semibold">Alerts</h1>
      <p className="mt-1 text-sm text-[#94A3B8]">In-app only. Created when a visit finds a HIGH or MEANINGFUL move since your previous visit.</p>
      <div className="mt-4 space-y-3">
        {rows === null ? <p className="text-sm text-[#94A3B8]">Loading…</p> : rows.length === 0 ? <p className="text-sm text-[#94A3B8]">No alerts yet.</p> : rows.map((n) => (
          <Card key={n.id} accent={n.read ? undefined : '#6366F1'}>
            <p className="font-semibold">{n.title}</p>
            <p className="text-sm text-[#CBD5E1]">{n.body}</p>
            <p className="mt-1 text-xs text-[#94A3B8]">{fmtDateTime(n.created_at)}</p>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-6">
      <Card><h1 className="text-2xl font-semibold">404</h1><p className="mt-2 text-sm text-[#94A3B8]">That page does not exist.</p></Card>
    </div>
  )
}
