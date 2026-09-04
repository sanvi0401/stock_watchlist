import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'
import { ChoiceCards, Select } from './Account'
import { SENSITIVITIES, TIMEZONES } from '../constants'

export default function Onboarding() {
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [name, setName] = useState('My Watchlist')
  const [symbols, setSymbols] = useState('NVDA, AAPL, MSFT, TSLA')
  const [timezone, setTimezone] = useState('Asia/Kolkata')
  const [sensitivity, setSensitivity] = useState('balanced')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  async function finish(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const list = symbols.split(',').map((s) => s.trim()).filter(Boolean)
      await api.patchSettings({ timezone, sensitivity, onboarding_complete: true })
      if (list.length) await api.createWatchlist({ name: name.trim() || 'My Watchlist', symbols: list, category: 'Core' })
      nav('/app/overview')
    } catch (ex) {
      setErr((ex as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const frames = [
    <Card key="welcome" className="max-w-lg">
      <h1 className="text-2xl font-semibold">Welcome to Smart Market Watch</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">We remember the price you last saw for every name you follow. When you come back, we tell you only what moved meaningfully, and why.</p>
      <Button className="mt-6" onClick={() => setStep(1)}>Set up</Button>
    </Card>,
    <Card key="prefs" className="w-full max-w-lg">
      <h1 className="text-2xl font-semibold">Your preferences</h1>
      <p className="mt-1 text-sm text-[#94A3B8]">You can change these later in Settings.</p>
      <form className="mt-4 space-y-4" onSubmit={(e) => { e.preventDefault(); setStep(2) }}>
        <div>
          <Label>Timezone</Label>
          <Select label="Timezone" value={timezone} onChange={setTimezone}>
            {TIMEZONES.map((z) => <option key={z} value={z}>{z.replace(/_/g, ' ')}</option>)}
          </Select>
        </div>
        <div>
          <Label>Sensitivity</Label>
          <ChoiceCards name="onboard-sensitivity" value={sensitivity} options={SENSITIVITIES} onPick={setSensitivity} />
        </div>
        <Button type="submit">Continue</Button>
      </form>
    </Card>,
    <Card key="list" className="w-full max-w-lg">
      <h1 className="text-2xl font-semibold">Your first watchlist</h1>
      <form className="mt-4 space-y-3" onSubmit={finish}>
        <div><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} required /></div>
        <div>
          <Label>Companies or tickers, comma separated</Label>
          <Input value={symbols} onChange={(e) => setSymbols(e.target.value)} placeholder="NVDA, Apple, Google" />
          <p className="mt-1 text-xs text-[#94A3B8]">Today’s price becomes each name’s baseline. Come back later to see what changed.</p>
        </div>
        {err ? <p className="text-sm text-loss">{err}</p> : null}
        <Button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Open Overview'}</Button>
      </form>
    </Card>,
  ]

  return <div className="flex min-h-screen items-center justify-center bg-surface p-6">{frames[step]}</div>
}
