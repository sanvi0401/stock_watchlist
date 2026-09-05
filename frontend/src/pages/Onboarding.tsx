import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'
import { TIMEZONES } from './Account'

export default function Onboarding() {
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [name, setName] = useState('Tech Stocks')
  const [symbols, setSymbols] = useState('NVDA, AAPL, MSFT, TSLA')
  const [timezone, setTimezone] = useState('America/New_York')
  const [sensitivity, setSensitivity] = useState('balanced')

  async function finish(e: FormEvent) {
    e.preventDefault()
    const list = symbols.split(',').map((s) => s.trim()).filter(Boolean)
    await api.patchSettings({ timezone, sensitivity, onboarding_complete: true })
    await api.createWatchlist({ name, symbols: list, category: 'Core' })
    nav('/app/overview')
  }

  const frames = [
    <Card key="w">
      <h1 className="text-2xl font-semibold">Welcome to Market Watch</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">We remember what you last saw and only escalate what is statistically unusual for each name.</p>
      <Button className="mt-6" onClick={() => setStep(1)}>Set up your desk</Button>
    </Card>,
    <Card key="desk">
      <h1 className="text-2xl font-semibold">Your desk</h1>
      <p className="mt-1 text-sm text-[#94A3B8]">Timezone for timestamps, and how aggressively we flag outliers. You can change this later in Settings. Prices stay in USD.</p>
      <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(2) }}>
        <div>
          <Label>Timezone</Label>
          <select value={timezone} onChange={(e) => setTimezone(e.target.value)} className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm">
            {TIMEZONES.map((z) => <option key={z} value={z}>{z.replace(/_/g, ' ')}</option>)}
          </select>
        </div>
        <div>
          <Label>Outlier sensitivity</Label>
          <select value={sensitivity} onChange={(e) => setSensitivity(e.target.value)} className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm">
            <option value="conservative">Conservative — fewer alerts</option>
            <option value="balanced">Balanced — default</option>
            <option value="sensitive">Sensitive — more outliers</option>
          </select>
        </div>
        <Button type="submit">Continue</Button>
      </form>
    </Card>,
    <Card key="c">
      <h1 className="text-2xl font-semibold">Create first watchlist</h1>
      <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(3) }}>
        <div><Label>Portfolio name</Label><Input value={name} onChange={(e) => setName(e.target.value)} /></div>
        <Button type="submit">Continue</Button>
      </form>
    </Card>,
    <Card key="a">
      <h1 className="text-2xl font-semibold">Add stocks</h1>
      <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(4) }}>
        <div><Label>Companies or tickers</Label><Input value={symbols} onChange={(e) => setSymbols(e.target.value)} /></div>
        <Button type="submit">Continue</Button>
      </form>
    </Card>,
    <Card key="d">
      <h1 className="text-2xl font-semibold">Setup complete</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">Your first check records a baseline only after you mark it as seen. Until then we will not claim a move since last check.</p>
      <form onSubmit={finish}><Button className="mt-6" type="submit">Open overview</Button></form>
    </Card>,
  ]

  return <div className="flex min-h-screen items-center justify-center bg-surface p-6">{frames[step]}</div>
}
