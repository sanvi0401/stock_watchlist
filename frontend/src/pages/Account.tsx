import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'
import { LegalModal } from '../components/LegalModal'
import { fmtWhen } from '../utils/format'

type SettingsForm = {
  name: string
  email: string
  timezone: string
  sensitivity: string
  lookback_mode: string
  in_app_alerts: boolean
  high_significance_only: boolean
  unusual_volume_emphasis: boolean
  created_at?: string
}

const EMPTY: SettingsForm = {
  name: '',
  email: '',
  timezone: 'America/New_York',
  sensitivity: 'balanced',
  lookback_mode: 'since_last_check',
  in_app_alerts: true,
  high_significance_only: false,
  unusual_volume_emphasis: true,
}

export const TIMEZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Sao_Paulo',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'Asia/Kolkata',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Sydney',
  'UTC',
]

const OUTLIERS = [
  {
    id: 'conservative',
    title: 'Conservative',
    body: 'Fewer outliers. Only stretched moves versus this name’s own volatility rank HIGH.',
  },
  {
    id: 'balanced',
    title: 'Balanced',
    body: 'Default. HIGH at 80+, MEANINGFUL at 60+, NOTABLE at 30+ after volatility scaling.',
  },
  {
    id: 'sensitive',
    title: 'Sensitive',
    body: 'More names flagged. Smaller moves can still count as outliers when you check often.',
  },
]

const LOOKBACKS = [
  { id: 'since_last_check', title: 'Since last check', body: 'Compare to the last price you marked as seen on Overview.' },
  { id: 'previous_close', title: 'Previous close', body: 'Compare to yesterday’s official close, not your last visit.' },
  { id: 'five_day', title: 'Five trading sessions', body: 'Compare to the close five sessions ago when enough daily history exists.' },
]

function Select({
  value,
  onChange,
  children,
}: {
  value: string
  onChange: (v: string) => void
  children: ReactNode
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm text-[#F8FAFC] outline-none focus:border-intel"
    >
      {children}
    </select>
  )
}

function ChoiceCards({
  name,
  value,
  options,
  onPick,
}: {
  name: string
  value: string
  options: { id: string; title: string; body: string }[]
  onPick: (id: string) => void
}) {
  return (
    <div className="grid gap-3">
      {options.map((opt) => {
        const on = value === opt.id
        return (
          <label
            key={opt.id}
            className={`flex cursor-pointer gap-3 rounded-lg border p-3 ${on ? 'border-intel bg-intel/10' : 'border-[#232F46] hover:border-[#2E3E5B]'}`}
          >
            <input
              type="radio"
              name={name}
              className="mt-1"
              checked={on}
              onChange={() => onPick(opt.id)}
            />
            <span>
              <span className="block font-medium capitalize">{opt.title}</span>
              <span className="mt-1 block text-sm text-[#94A3B8]">{opt.body}</span>
            </span>
          </label>
        )
      })}
    </div>
  )
}

function payload(form: SettingsForm) {
  return {
    name: form.name,
    timezone: form.timezone,
    sensitivity: form.sensitivity,
    lookback_mode: form.lookback_mode,
    in_app_alerts: form.in_app_alerts,
    high_significance_only: form.high_significance_only,
    unusual_volume_emphasis: form.unusual_volume_emphasis,
  }
}

export function SettingsPage() {
  const [form, setForm] = useState<SettingsForm>(EMPTY)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    api.settings().then((s) => setForm({ ...EMPTY, ...(s as SettingsForm) })).catch((e) => setErr(e.message))
  }, [])

  async function persist(next: SettingsForm, notice: string) {
    setSaving(true)
    setErr('')
    setMsg('')
    try {
      const saved = await api.patchSettings(payload(next)) as SettingsForm
      setForm({ ...EMPTY, ...saved })
      setMsg(notice)
    } catch (e) {
      setErr((e as Error).message || 'Could not save settings')
    } finally {
      setSaving(false)
    }
  }

  async function save(e: FormEvent) {
    e.preventDefault()
    await persist(form, 'Settings saved. Overview will use these outlier rules on the next check.')
  }

  return (
    <form className="max-w-3xl space-y-6" onSubmit={save}>
      <h1 className="text-[30px] font-semibold">System Settings & Intelligence Controls</h1>
      <p className="text-sm text-[#94A3B8]">
        Outlier sensitivity is applied immediately when you pick a card — you do not have to hunt for a hidden save on that control.
      </p>
      <Card>
        <h2 className="mb-3 font-semibold">Personal & analytical locale</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <div><Label>Full name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          <div><Label>Work email</Label><Input value={form.email} disabled /></div>
          <div>
            <Label>Timezone (used for all timestamps in the app)</Label>
            <Select value={form.timezone} onChange={(timezone) => setForm({ ...form, timezone })}>
              {TIMEZONES.map((z) => <option key={z} value={z}>{z.replace(/_/g, ' ')}</option>)}
            </Select>
          </div>
          <p className="text-sm text-[#94A3B8] md:col-span-2">Prices are delayed USD prints. Currency conversion is not offered.</p>
        </div>
      </Card>
      <Card>
        <h2 className="mb-1 font-semibold">Outlier / anomaly sensitivity</h2>
        <p className="mb-3 text-sm text-[#94A3B8]">Three modes. Conservative hides noise; sensitive flags more names as outliers.</p>
        <ChoiceCards
          name="sensitivity"
          value={form.sensitivity}
          options={OUTLIERS}
          onPick={(sensitivity) => {
            const next = { ...form, sensitivity }
            setForm(next)
            void persist(next, `${OUTLIERS.find((o) => o.id === sensitivity)?.title} outlier mode is on.`)
          }}
        />
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">In-app alerts (preferences only)</h2>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.in_app_alerts} onChange={(e) => setForm({ ...form, in_app_alerts: e.target.checked })} />
          Show change cards on Overview / Notifications
        </label>
        <p className="mt-2 text-xs text-[#94A3B8]">This does not send email or push. Meaningful changes appear in the app after you open Overview.</p>
      </Card>
      {err ? <p className="text-sm text-loss">{err}</p> : null}
      {msg ? <p className="text-sm text-gain">{msg}</p> : null}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</Button>
        <Link to="/app/profile" className="self-center text-sm text-primary">Profile</Link>
        <Link to="/app/preferences" className="self-center text-sm text-primary">Preferences</Link>
      </div>
    </form>
  )
}

export function ProfilePage() {
  const [me, setMe] = useState<SettingsForm | null>(null)
  const [lists, setLists] = useState(0)
  const [symbols, setSymbols] = useState(0)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [legal, setLegal] = useState<null | 'terms' | 'privacy'>(null)
  useEffect(() => {
    Promise.all([api.me(), api.settings(), api.watchlists()])
      .then(([user, settings, watchlists]) => {
        const u = user as { name: string; email: string; timezone: string; sensitivity: string; lookback_mode: string; onboarding_complete: boolean; created_at?: string }
        const s = settings as SettingsForm
        setMe({
          ...EMPTY,
          ...s,
          name: u.name || s.name,
          email: u.email || s.email,
          timezone: u.timezone || s.timezone,
          sensitivity: u.sensitivity || s.sensitivity,
          lookback_mode: u.lookback_mode || s.lookback_mode,
          created_at: u.created_at || s.created_at,
        })
        setLists(watchlists.length)
        setSymbols(watchlists.reduce((n, w) => n + (w.stock_count || 0), 0))
      })
      .catch((e) => setErr(e.message))
  }, [])

  async function save(e: FormEvent) {
    e.preventDefault()
    if (!me) return
    try {
      const saved = await api.patchSettings({ name: me.name, timezone: me.timezone }) as SettingsForm
      setMe({ ...me, ...saved })
      setMsg('Profile updated.')
      setErr('')
    } catch (ex) {
      setErr((ex as Error).message)
    }
  }

  if (err && !me) return <Card><p className="text-sm text-loss">{err}</p></Card>
  if (!me) return <Card><p className="text-sm text-[#94A3B8]">Loading profile…</p></Card>
  const outlier = OUTLIERS.find((o) => o.id === me.sensitivity)
  const lookback = LOOKBACKS.find((o) => o.id === me.lookback_mode)

  return (
    <form className="max-w-2xl space-y-4" onSubmit={save}>
      <h1 className="text-[30px] font-semibold">Profile</h1>
      <Card>
        <div className="grid gap-3 md:grid-cols-2">
          <div><Label>Full name</Label><Input value={me.name} onChange={(e) => setMe({ ...me, name: e.target.value })} /></div>
          <div><Label>Email</Label><Input value={me.email} disabled /></div>
          <div>
            <Label>Timezone</Label>
            <Select value={me.timezone} onChange={(timezone) => setMe({ ...me, timezone })}>
              {TIMEZONES.map((z) => <option key={z} value={z}>{z.replace(/_/g, ' ')}</option>)}
            </Select>
          </div>
        </div>
        <Button className="mt-4" type="submit">Save profile</Button>
        {msg ? <p className="mt-2 text-sm text-gain">{msg}</p> : null}
        {err ? <p className="mt-2 text-sm text-loss">{err}</p> : null}
      </Card>
      <Card>
        <h2 className="font-semibold">Account snapshot</h2>
        <dl className="mt-3 grid gap-3 text-sm md:grid-cols-2">
          <div><dt className="text-[#94A3B8]">Member since</dt><dd>{me.created_at ? fmtWhen(me.created_at) : 'This session'}</dd></div>
          <div><dt className="text-[#94A3B8]">Watchlists</dt><dd>{lists}</dd></div>
          <div><dt className="text-[#94A3B8]">Names tracked</dt><dd>{symbols}</dd></div>
          <div><dt className="text-[#94A3B8]">Outlier mode</dt><dd className="capitalize">{outlier?.title || me.sensitivity}</dd></div>
          <div><dt className="text-[#94A3B8]">Lookback</dt><dd>{lookback?.title || me.lookback_mode}</dd></div>
          <div><dt className="text-[#94A3B8]">In-app alerts</dt><dd>{me.in_app_alerts ? 'On' : 'Off'}</dd></div>
        </dl>
        <p className="mt-4 text-sm text-[#94A3B8]">
          Legal:{' '}
          <button type="button" className="text-primary underline" onClick={() => setLegal('terms')}>Terms of Service</button>
          {' · '}
          <button type="button" className="text-primary underline" onClick={() => setLegal('privacy')}>Privacy Policy</button>
        </p>
      </Card>
      <LegalModal kind={legal} onClose={() => setLegal(null)} />
    </form>
  )
}

export function PreferencesPage() {
  const [form, setForm] = useState<SettingsForm>(EMPTY)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => {
    api.settings().then((s) => setForm({ ...EMPTY, ...(s as SettingsForm) })).catch((e) => setErr(e.message))
  }, [])

  async function pick(partial: Partial<SettingsForm>, notice: string) {
    const next = { ...form, ...partial }
    setForm(next)
    try {
      const saved = await api.patchSettings(payload(next)) as SettingsForm
      setForm({ ...EMPTY, ...saved })
      setMsg(notice)
      setErr('')
    } catch (e) {
      setErr((e as Error).message)
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-[30px] font-semibold">Preferences</h1>
      <p className="text-sm text-[#94A3B8]">These controls change how outliers are scored and which moves land on Overview.</p>
      <Card>
        <h2 className="mb-3 font-semibold">Outlier sensitivity</h2>
        <ChoiceCards
          name="pref-sensitivity"
          value={form.sensitivity}
          options={OUTLIERS}
          onPick={(sensitivity) => void pick({ sensitivity }, `Outlier mode set to ${sensitivity}.`)}
        />
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">Lookback window</h2>
        <ChoiceCards
          name="pref-lookback"
          value={form.lookback_mode}
          options={LOOKBACKS}
          onPick={(lookback_mode) => void pick({ lookback_mode }, 'Lookback updated.')}
        />
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">Overview filters</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.high_significance_only}
            onChange={(e) => void pick({ high_significance_only: e.target.checked }, e.target.checked ? 'Overview will only highlight HIGH outliers.' : 'Overview will show notable and meaningful moves again.')}
          />
          Show only high-significance outliers on Overview
        </label>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.unusual_volume_emphasis}
            onChange={(e) => void pick({ unusual_volume_emphasis: e.target.checked }, e.target.checked ? 'Volume gets more weight in the score.' : 'Volume weight reduced.')}
          />
          Emphasize unusual volume in the significance score (session-scaled vs typical volume; not dark-pool data)
        </label>
      </Card>
      {err ? <p className="text-sm text-loss">{err}</p> : null}
      {msg ? <p className="text-sm text-gain">{msg}</p> : null}
      <Link to="/app/settings" className="text-sm text-primary">All settings →</Link>
    </div>
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
          <Card key={n.id}><p className="font-semibold">{n.title}</p><p className="text-sm text-[#CBD5E1]">{n.body}</p><p className="text-xs text-[#94A3B8]">{fmtWhen(n.created_at)}</p></Card>
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
