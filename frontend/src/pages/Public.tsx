import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, api, setToken } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-surface">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2">
          <img src="/logo.svg" className="h-8" alt="Market Watch" />
        </div>
        <nav className="hidden items-center gap-6 text-sm text-on-surface-variant md:flex">
          <a href="#features">Features</a>
          <a href="#intelligence">Intelligence</a>
          <a href="#methodology">Methodology</a>
        </nav>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-on-surface">Log In</Link>
          <Link to="/signup"><Button>Get Started</Button></Link>
        </div>
      </header>
      <div className="border-y border-[#232F46] bg-[#0B0F17] px-6 py-2 font-mono text-xs text-on-surface-variant">
        SPY 518.32 <span className="text-gain">+0.42%</span> · QQQ 446.12 <span className="text-gain">+0.81%</span> · NVDA 126.88 <span className="text-gain">+5.82%</span> · TSLA 174.60 <span className="text-loss">-5.21%</span>
      </div>
      <section className="mx-auto max-w-3xl px-6 py-20 text-center">
        <h1 className="text-4xl font-semibold tracking-tight md:text-[40px] md:leading-[48px]">Know what changed. Know what matters.</h1>
        <p className="mt-4 text-on-surface-variant">
          Smart Market Watch remembers what you last saw, scores unusual movement against each name’s own volatility, and tells you why it deserves attention.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link to="/signup"><Button>Get Started</Button></Link>
          <Link to="/login"><Button variant="outline">Explore Terminal View</Button></Link>
        </div>
      </section>
      <section id="features" className="mx-auto grid max-w-6xl gap-4 px-6 pb-16 md:grid-cols-3">
        {[
          ['Track', 'Last-seen baselines per symbol, not a generic price ticker.'],
          ['Detect', 'Significance from price abnormality, volume, and volatility — not raw %.'],
          ['Understand', 'Plain-language “why this matters” on every high-priority move.'],
        ].map(([t, b]) => (
          <Card key={t}>
            <h3 className="text-xl font-semibold">{t}</h3>
            <p className="mt-2 text-sm text-[#CBD5E1]">{b}</p>
          </Card>
        ))}
      </section>
    </div>
  )
}

function AuthFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-10">
      <Card className="w-full max-w-md p-8">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">Market Watch Terminal</p>
        <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
        {children}
      </Card>
    </div>
  )
}

export function SignUpPage() {
  const nav = useNavigate()
  const [err, setErr] = useState('')
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    try {
      const res = await api.register({
        name: String(fd.get('name')),
        email: String(fd.get('email')),
        password: String(fd.get('password')),
      })
      setToken(res.access_token)
      nav('/onboarding')
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : 'Could not create account')
    }
  }
  return (
    <AuthFrame title="Create your Market Watch account">
      <p className="mt-1 text-sm text-[#94A3B8]">Set up intelligent watchlist monitoring in under 2 minutes.</p>
      <form className="mt-6 space-y-3" onSubmit={onSubmit}>
        <div><Label>Full Name</Label><Input name="name" required defaultValue="Sanvi Patel" /></div>
        <div><Label>Work / Investor Email</Label><Input name="email" type="email" required /></div>
        <div><Label>Password</Label><Input name="password" type="password" minLength={8} required /></div>
        <label className="flex items-center gap-2 text-sm text-[#CBD5E1]"><input type="checkbox" required /> I agree to the Terms of Service and Privacy Policy</label>
        {err ? <p className="text-sm text-loss">{err}</p> : null}
        <Button className="w-full" type="submit">Create Account →</Button>
      </form>
      <p className="mt-4 text-sm">Already have an account? <Link className="text-primary" to="/login">Log In</Link></p>
    </AuthFrame>
  )
}

export function LoginPage() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const [err, setErr] = useState(params.get('expired') ? 'Your session expired. Please sign in again.' : '')
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    try {
      const res = await api.login({ email: String(fd.get('email')), password: String(fd.get('password')) })
      setToken(res.access_token)
      nav(res.onboarding_complete ? '/app/overview' : '/onboarding')
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : 'Sign in failed')
    }
  }
  return (
    <AuthFrame title="Welcome back">
      <form className="mt-6 space-y-3" onSubmit={onSubmit}>
        <div><Label>Email</Label><Input name="email" type="email" required /></div>
        <div><Label>Password</Label><Input name="password" type="password" required /></div>
        {err ? <p className="text-sm text-loss">{err}</p> : null}
        <Button className="w-full" type="submit">Log In</Button>
      </form>
      <p className="mt-4 text-sm"><Link className="text-primary" to="/forgot-password">Forgot password</Link></p>
      <p className="mt-2 text-sm">Need an account? <Link className="text-primary" to="/signup">Sign Up</Link></p>
    </AuthFrame>
  )
}

export function ForgotPage() {
  const [msg, setMsg] = useState('')
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const res = await api.forgot(String(fd.get('email')))
    setMsg(res.dev_reset_token ? `Dev reset token: ${res.dev_reset_token}` : 'If that email exists, a reset link was issued.')
  }
  return (
    <AuthFrame title="Reset your password">
      <form className="mt-6 space-y-3" onSubmit={onSubmit}>
        <div><Label>Email</Label><Input name="email" type="email" required /></div>
        <Button className="w-full" type="submit">Send reset link</Button>
      </form>
      {msg ? <p className="mt-3 text-sm text-secondary break-all">{msg}</p> : null}
    </AuthFrame>
  )
}

export function ResetPage() {
  const [params] = useSearchParams()
  const nav = useNavigate()
  const [err, setErr] = useState('')
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    try {
      await api.reset(params.get('token') || String(fd.get('token')), String(fd.get('password')))
      nav('/login')
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : 'Reset failed')
    }
  }
  return (
    <AuthFrame title="Choose a new password">
      <form className="mt-6 space-y-3" onSubmit={onSubmit}>
        {!params.get('token') ? <div><Label>Token</Label><Input name="token" required /></div> : null}
        <div><Label>New password</Label><Input name="password" type="password" minLength={8} required /></div>
        {err ? <p className="text-sm text-loss">{err}</p> : null}
        <Button className="w-full" type="submit">Update password</Button>
      </form>
    </AuthFrame>
  )
}
