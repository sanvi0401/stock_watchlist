import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'

export default function Onboarding() {
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [name, setName] = useState('Tech Stocks')
  const [symbols, setSymbols] = useState('NVDA, AAPL, MSFT, TSLA')

  async function finish(e: FormEvent) {
    e.preventDefault()
    const list = symbols.split(',').map((s) => s.trim()).filter(Boolean)
    await api.createWatchlist({ name, symbols: list, category: 'Core' })
    await api.patchSettings({ onboarding_complete: true })
    nav('/app/overview')
  }

  const frames = [
    <Card key="w">
      <h1 className="text-2xl font-semibold">Welcome to Market Watch</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">We remember what you last saw and only escalate what is statistically unusual for each name.</p>
      <Button className="mt-6" onClick={() => setStep(1)}>Create first watchlist</Button>
    </Card>,
    <Card key="c">
      <h1 className="text-2xl font-semibold">Create first watchlist</h1>
      <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(2) }}>
        <div><Label>Portfolio name</Label><Input value={name} onChange={(e) => setName(e.target.value)} /></div>
        <Button type="submit">Continue</Button>
      </form>
    </Card>,
    <Card key="a">
      <h1 className="text-2xl font-semibold">Add stocks</h1>
      <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(3) }}>
        <div><Label>Tickers</Label><Input value={symbols} onChange={(e) => setSymbols(e.target.value)} /></div>
        <Button type="submit">Continue</Button>
      </form>
    </Card>,
    <Card key="d">
      <h1 className="text-2xl font-semibold">Setup complete</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">Your first check will record baselines. The next visit answers what changed since then.</p>
      <form onSubmit={finish}><Button className="mt-6" type="submit">Open overview</Button></form>
    </Card>,
  ]

  return <div className="flex min-h-screen items-center justify-center bg-surface p-6">{frames[step]}</div>
}
