import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'
import AuthenticatorGuide from '../components/AuthenticatorGuide'
import { TIMEZONES } from './Account'
import { QRCodeSVG } from 'qrcode.react'

export default function Onboarding() {
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [name, setName] = useState('Tech Stocks')
  const [symbols, setSymbols] = useState('NVDA, AAPL, MSFT, TSLA')
  const [timezone, setTimezone] = useState('America/New_York')
  const [sensitivity, setSensitivity] = useState('balanced')
  const [secret, setSecret] = useState('')
  const [uri, setUri] = useState('')
  const [code, setCode] = useState('')
  const [securityError, setSecurityError] = useState('')
  const [securityLoading, setSecurityLoading] = useState(false)

  async function startAuthenticator() {
    setSecurityError('')
    setSecurityLoading(true)
    try {
      const r = await api.totpSetup()
      if (r.configured) setStep(5)
      else { setSecret(r.secret || ''); setUri(r.otpauth_uri || '') }
    } catch (e) { setSecurityError(e instanceof ApiError ? e.message : 'Could not start authenticator setup') }
    finally { setSecurityLoading(false) }
  }

  async function verifyAuthenticator(e: FormEvent) {
    e.preventDefault()
    setSecurityError(''); setSecurityLoading(true)
    try { await api.totpVerify(code); setStep(5) }
    catch (e) { setSecurityError(e instanceof ApiError ? e.message : 'Invalid authenticator code') }
    finally { setSecurityLoading(false) }
  }

  async function finish(e: FormEvent) {
    e.preventDefault()
    const list = symbols.split(',').map((s) => s.trim()).filter(Boolean)
    await api.patchSettings({ timezone, sensitivity, onboarding_complete: true })
    await api.createWatchlist({ name, symbols: list, category: 'Core' })
    nav('/app/overview')
  }

  const frames = [
    <Card key="w"><h1 className="text-2xl font-semibold">Welcome to Market Watch</h1><p className="mt-2 text-sm text-[#94A3B8]">We remember what you last saw and only escalate what is statistically unusual for each name.</p><Button className="mt-6" onClick={() => setStep(1)}>Set up your desk</Button></Card>,
    <Card key="desk"><h1 className="text-2xl font-semibold">Your desk</h1><p className="mt-1 text-sm text-[#94A3B8]">Timezone for timestamps, and how aggressively we flag outliers. You can change this later in Settings. Prices stay in USD.</p><form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(2) }}><div><Label>Timezone</Label><select value={timezone} onChange={(e) => setTimezone(e.target.value)} className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm">{TIMEZONES.map((z) => <option key={z} value={z}>{z.replace(/_/g, ' ')}</option>)}</select></div><div><Label>Outlier sensitivity</Label><select value={sensitivity} onChange={(e) => setSensitivity(e.target.value)} className="h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm"><option value="conservative">Conservative — fewer alerts</option><option value="balanced">Balanced — default</option><option value="sensitive">Sensitive — more outliers</option></select></div><Button type="submit">Continue</Button></form></Card>,
    <Card key="c"><h1 className="text-2xl font-semibold">Create first watchlist</h1><form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(3) }}><div><Label>Portfolio name</Label><Input value={name} onChange={(e) => setName(e.target.value)} /></div><Button type="submit">Continue</Button></form></Card>,
    <Card key="a"><h1 className="text-2xl font-semibold">Add stocks</h1><form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); setStep(4) }}><div><Label>Companies or tickers</Label><Input value={symbols} onChange={(e) => setSymbols(e.target.value)} /></div><Button type="submit">Continue</Button></form></Card>,
    <Card key="security" className="w-full max-w-2xl"><h1 className="text-2xl font-semibold">Secure your account</h1><p className="mt-2 text-sm text-[#94A3B8]">Set up Google Authenticator now. You will use its 6-digit code if you ever need to recover your password.</p><div className="mt-5 flex flex-wrap items-center gap-3"><Button onClick={startAuthenticator} disabled={securityLoading}>{securityLoading ? 'Preparing…' : 'Set up Authenticator'}</Button><AuthenticatorGuide /></div>{!secret ? null : <form className="mt-5 space-y-5" onSubmit={verifyAuthenticator}>{uri ? <div className="flex flex-col items-center gap-3 rounded-lg border border-[#334155] bg-white p-4"><QRCodeSVG value={uri} size={220} level="M" includeMargin={true} aria-label="Authenticator setup QR code" /><p className="text-center text-xs text-slate-600">Open Google Authenticator, tap +, choose Scan a QR code, and scan this code.</p></div> : null}<div><Label>Manual setup key</Label><Input readOnly value={secret} /></div><p className="text-xs text-[#94A3B8] break-all">If you cannot scan the QR code, enter this setup key manually in your authenticator app.</p><div><Label>6-digit code</Label><Input inputMode="numeric" autoComplete="one-time-code" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} /></div>{securityError ? <p className="text-sm text-loss">{securityError}</p> : null}<Button type="submit" disabled={securityLoading || code.length !== 6}>{securityLoading ? 'Verifying…' : 'Verify and continue'}</Button></form>}{securityError && !secret ? <p className="mt-3 text-sm text-loss">{securityError}</p> : null}</Card>,
    <Card key="d"><h1 className="text-2xl font-semibold">Setup complete</h1><p className="mt-2 text-sm text-[#94A3B8]">Your account is protected. If you forget your password, you can recover it with the authenticator code you just configured.</p><form onSubmit={finish}><Button className="mt-6" type="submit">Open overview</Button></form></Card>,
  ]

  return <div className="flex min-h-screen items-center justify-center bg-surface p-6">{frames[step]}</div>
}
