import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../services/api'
import { Button, Card, Input, Label } from '../components/ui'

export function SecurityPage() {
  const [enabled, setEnabled] = useState(false)
  const [secret, setSecret] = useState('')
  const [uri, setUri] = useState('')
  const [code, setCode] = useState('')
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => { api.totpStatus().then((r) => setEnabled(r.enabled)).catch((e) => setErr(e.message)) }, [])

  async function setup() {
    setErr(''); setMsg(''); setLoading(true)
    try {
      const r = await api.totpSetup()
      setSecret(r.secret || '')
      setUri(r.otpauth_uri || '')
      setMsg('Scan the QR code in Google Authenticator, then enter the 6-digit code below.')
    } catch (e) { setErr(e instanceof ApiError ? e.message : 'Could not start setup') }
    finally { setLoading(false) }
  }

  async function verify() {
    setErr(''); setMsg(''); setLoading(true)
    try {
      await api.totpVerify(code)
      setEnabled(true); setSecret(''); setUri(''); setCode('')
      setMsg('Authenticator is enabled. You can now use it to recover your password.')
    } catch (e) { setErr(e instanceof ApiError ? e.message : 'Invalid authenticator code') }
    finally { setLoading(false) }
  }

  return <div className="max-w-2xl space-y-6">
    <div><h1 className="text-[30px] font-semibold">Security</h1><p className="mt-1 text-sm text-[#94A3B8]">Set up an authenticator app for free password recovery.</p></div>
    <Card>
      <h2 className="font-semibold">Authenticator app</h2>
      <p className="mt-2 text-sm text-[#94A3B8]">Use Google Authenticator or another TOTP app. Your code changes every 30 seconds.</p>
      {enabled ? <p className="mt-4 text-sm text-gain">✓ Authenticator enabled</p> : <>
        {!secret ? <Button className="mt-4" onClick={setup} disabled={loading}>{loading ? 'Preparing…' : 'Set up Authenticator'}</Button> : <div className="mt-4 space-y-4">
          <div><Label>Setup key</Label><Input readOnly value={secret} /></div>
          <p className="text-xs text-[#94A3B8] break-all">If your authenticator supports it, use this setup URI: {uri}</p>
          <div><Label>6-digit code</Label><Input inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} /></div>
          <Button onClick={verify} disabled={loading || code.length !== 6}>{loading ? 'Verifying…' : 'Verify and enable'}</Button>
        </div>}
      </>}
      {msg ? <p className="mt-3 text-sm text-gain">{msg}</p> : null}
      {err ? <p className="mt-3 text-sm text-loss">{err}</p> : null}
    </Card>
    <Link to="/app/settings" className="text-sm text-primary">← Back to settings</Link>
  </div>
}

export function RecoverPasswordPage() {
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(''); setMsg(''); setLoading(true)
    try {
      const r = await api.recoverPassword(email, code, password)
      setMsg(r.message)
      setTimeout(() => nav('/login'), 900)
    } catch (e) { setErr(e instanceof ApiError ? e.message : 'Could not reset password') }
    finally { setLoading(false) }
  }

  return <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-10">
    <Card className="w-full max-w-md p-8">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-[#94A3B8]">Market Watch Terminal</p>
      <h1 className="mt-2 text-2xl font-semibold">Recover your password</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">Enter the email on your account and the current 6-digit code from your authenticator app.</p>
      <form className="mt-6 space-y-3" onSubmit={submit}>
        <div><Label>Email</Label><Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div><Label>Authenticator code</Label><Input inputMode="numeric" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} /></div>
        <div><Label>New password</Label><Input type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        {err ? <p className="text-sm text-loss">{err}</p> : null}
        {msg ? <p className="text-sm text-gain">{msg}</p> : null}
        <Button className="w-full" type="submit" disabled={loading}>{loading ? 'Updating…' : 'Reset password'}</Button>
      </form>
      <p className="mt-4 text-sm"><Link className="text-primary" to="/login">Back to login</Link></p>
    </Card>
  </div>
}
