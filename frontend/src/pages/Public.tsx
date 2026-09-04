import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, api, setToken } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'
import { LegalModal } from '../components/LegalModal'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-20 mx-auto flex max-w-6xl items-center justify-between bg-surface/95 px-6 py-5 backdrop-blur">
        <div className="flex items-center gap-2">
          <img src="/logo.svg" className="h-8" alt="Market Watch" />
        </div>
        <nav className="flex flex-wrap items-center justify-center gap-4 text-sm text-on-surface-variant">
          <a href="#features">Features</a>
          <a href="#intelligence">Intelligence</a>
          <a href="#methodology">Methodology</a>
        </nav>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-on-surface">Log In</Link>
          <Link to="/signup"><Button>Get Started</Button></Link>
        </div>
      </header>
      <section className="mx-auto max-w-3xl px-6 py-20 text-center">
        <h1 className="text-4xl font-semibold tracking-tight md:text-[40px] md:leading-[48px]">Know what changed. Know what matters.</h1>
        <p className="mt-4 text-on-surface-variant">
          Smart Market Watch remembers what you last saw, scores unusual movement against each name’s own volatility, and tells you why it deserves attention.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link to="/signup"><Button>Get Started</Button></Link>
          <Link to="/login"><Button variant="outline">Log in</Button></Link>
        </div>
      </section>
      <section id="features" className="mx-auto grid max-w-6xl gap-4 px-6 pb-16 md:grid-cols-3">
        {[
          ['Track', 'Last-seen baselines per symbol, not a generic price ticker. We remember the last price you actually looked at.'],
          ['Detect', 'Significance from price abnormality, volume, and volatility — not raw %. A 2% move in NVDA is not the same as 2% in COST.'],
          ['Understand', 'Plain-language “why this matters” on every high-priority move, with evidence you can audit.'],
        ].map(([t, b]) => (
          <Card key={t}>
            <h3 className="text-xl font-semibold">{t}</h3>
            <p className="mt-2 text-sm text-[#CBD5E1]">{b}</p>
          </Card>
        ))}
      </section>
      <section id="intelligence" className="mx-auto max-w-6xl px-6 pb-16">
        <Card>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">Intelligence</p>
          <h2 className="mt-1 text-2xl font-semibold">What is actually different from a watchlist?</h2>
          <div className="mt-4 grid gap-6 md:grid-cols-2">
            <div>
              <h3 className="font-semibold text-primary">Last-seen state</h3>
              <p className="mt-2 text-sm text-[#CBD5E1]">When you open Overview we compare today to the price you saw on your previous visit — not yesterday’s close. Refreshing within a visit keeps the same baseline. The first visit records a baseline and never claims a fake “move.”</p>
            </div>
            <div>
              <h3 className="font-semibold text-primary">Significance 0–100</h3>
              <p className="mt-2 text-sm text-[#CBD5E1]">STABLE 0–29 · NOTABLE 30–59 · MEANINGFUL 60–79 · HIGH 80–100. The move is measured in units of that name’s own typical daily range, so noisy names do not constantly scream. Volume can back up a move but never invent one.</p>
            </div>
            <div>
              <h3 className="font-semibold text-primary">Why this matters</h3>
              <p className="mt-2 text-sm text-[#CBD5E1]">Every ranked name includes an explanation and evidence (percent since last check, volume vs typical, data freshness). You can open the stock briefing for the full write-up.</p>
            </div>
            <div>
              <h3 className="font-semibold text-primary">Data honesty</h3>
              <p className="mt-2 text-sm text-[#CBD5E1]">Quotes are labeled LIVE, DELAYED, STALE, or UNAVAILABLE. Yahoo delayed quotes are the default. Unavailable prints never overwrite a valid last-seen price.</p>
            </div>
          </div>
        </Card>
      </section>
      <section id="methodology" className="mx-auto max-w-6xl px-6 pb-24">
        <Card>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">Methodology</p>
          <h2 className="mt-1 text-2xl font-semibold">How a check is calculated</h2>
          <ol className="mt-4 list-decimal space-y-3 pl-5 text-sm text-[#CBD5E1]">
            <li>Load your previous last-seen price for each symbol on your watchlists.</li>
            <li>Fetch a delayed Yahoo quote (price, previous close, volume, 52-week range, short sparkline).</li>
            <li>Compute percent change since you last looked, and today’s percent vs previous close.</li>
            <li>Score the move against that symbol’s recent volatility and whether volume is unusual.</li>
            <li>Write a short explanation, rank HIGH → MEANINGFUL → NOTABLE → STABLE, then record this visit so the next one compares against it.</li>
          </ol>
          <p className="mt-4 text-sm text-[#94A3B8]">This is monitoring, not advice. Delayed data can lag the tape by minutes. Add names by company (“Google”) or ticker (GOOGL) from Discover or a watchlist.</p>
        </Card>
      </section>
      <footer className="border-t border-[#232F46] px-6 py-8 text-center text-sm text-[#94A3B8]">
        <LandingLegal />
      </footer>
    </div>
  )
}

function LandingLegal() {
  const [legal, setLegal] = useState<null | 'terms' | 'privacy'>(null)
  return (
    <>
      <button type="button" className="text-primary underline" onClick={() => setLegal('terms')}>Terms of Service</button>
      <span className="mx-2">·</span>
      <button type="button" className="text-primary underline" onClick={() => setLegal('privacy')}>Privacy Policy</button>
      <LegalModal kind={legal} onClose={() => setLegal(null)} />
    </>
  )
}

function AuthFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-10">
      <Card className="w-full max-w-md p-8">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">Smart Market Watch</p>
        <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
        {children}
      </Card>
    </div>
  )
}

export function SignUpPage() {
  const nav = useNavigate()
  const [err, setErr] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [legal, setLegal] = useState<null | 'terms' | 'privacy'>(null)
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!agreed) {
      setErr('Open and agree to the Terms of Service and Privacy Policy to continue.')
      return
    }
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
      <p className="mt-1 text-sm text-[#94A3B8]">Takes about a minute. No email verification in this demo.</p>
      <form className="mt-6 space-y-3" onSubmit={onSubmit}>
        <div><Label>Full Name</Label><Input name="name" required autoComplete="name" /></div>
        <div><Label>Email</Label><Input name="email" type="email" required autoComplete="email" /></div>
        <div><Label>Password</Label><Input name="password" type="password" minLength={8} maxLength={72} required autoComplete="new-password" /></div>
        <label className="flex items-start gap-2 text-sm text-[#CBD5E1]">
          <input type="checkbox" className="mt-1" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} required />
          <span>
            I agree to the{' '}
            <button type="button" className="text-primary underline" onClick={() => setLegal('terms')}>Terms of Service</button>
            {' '}and{' '}
            <button type="button" className="text-primary underline" onClick={() => setLegal('privacy')}>Privacy Policy</button>
            . Open each to read them before creating an account.
          </span>
        </label>
        {err ? <p className="text-sm text-loss">{err}</p> : null}
        <Button className="w-full" type="submit">Create Account →</Button>
      </form>
      <p className="mt-4 text-sm">Already have an account? <Link className="text-primary" to="/login">Log In</Link></p>
      <LegalModal kind={legal} onClose={() => setLegal(null)} />
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
  const [resetUrl, setResetUrl] = useState('')
  const [err, setErr] = useState('')
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setErr('')
    setResetUrl('')
    const fd = new FormData(e.currentTarget)
    try {
      const res = await api.forgot(String(fd.get('email')))
      setMsg(res.message || 'If that email exists, a reset link was issued.')
      if (res.reset_url) setResetUrl(res.reset_url)
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : 'Could not start a reset')
    }
  }
  return (
    <AuthFrame title="Reset your password">
      <p className="mt-2 text-sm text-[#94A3B8]">
        This demo has no email service. Outside production the one-time reset link is shown here instead.
      </p>
      <form className="mt-6 space-y-3" onSubmit={onSubmit}>
        <div><Label>Email</Label><Input name="email" type="email" required /></div>
        <Button className="w-full" type="submit">Create reset link</Button>
      </form>
      {err ? <p className="mt-3 text-sm text-loss">{err}</p> : null}
      {msg ? <p className="mt-3 text-sm text-[#CBD5E1]">{msg}</p> : null}
      {resetUrl ? (
        <p className="mt-3 text-sm">
          <a className="text-primary break-all underline" href={resetUrl}>Open password reset link</a>
        </p>
      ) : null}
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
