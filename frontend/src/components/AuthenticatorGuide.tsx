import { useState } from 'react'
import { Button } from './ui'

function StepIcon({ step }: { step: 1 | 2 | 3 }) {
  return (
    <div className="flex h-20 w-20 items-center justify-center rounded-2xl border border-[#334155] bg-[#0B0F17] text-3xl">
      {step === 1 ? '📱' : step === 2 ? '▦' : '🔢'}
    </div>
  )
}

export default function AuthenticatorGuide() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>How to use Authenticator</Button>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-labelledby="auth-guide-title">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl border border-[#334155] bg-[#0F172A] p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#94A3B8]">Account security</p>
                <h2 id="auth-guide-title" className="mt-1 text-2xl font-semibold">How to use Google Authenticator</h2>
                <p className="mt-2 text-sm text-[#94A3B8]">Set it up once and use the 6-digit code whenever you need to recover your password.</p>
              </div>
              <button className="text-xl text-[#94A3B8] hover:text-white" onClick={() => setOpen(false)} aria-label="Close guide">×</button>
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-[#232F46] bg-[#111827] p-4">
                <StepIcon step={1} />
                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-primary">Step 1</p>
                <h3 className="mt-1 font-semibold">Install the app</h3>
                <p className="mt-2 text-sm text-[#94A3B8]">Install Google Authenticator on your phone and open it.</p>
              </div>
              <div className="rounded-lg border border-[#232F46] bg-[#111827] p-4">
                <StepIcon step={2} />
                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-primary">Step 2</p>
                <h3 className="mt-1 font-semibold">Scan the QR code</h3>
                <p className="mt-2 text-sm text-[#94A3B8]">Tap <b>+</b> → <b>Scan a QR code</b>, then scan the code shown by Market Watch.</p>
              </div>
              <div className="rounded-lg border border-[#232F46] bg-[#111827] p-4">
                <StepIcon step={3} />
                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-primary">Step 3</p>
                <h3 className="mt-1 font-semibold">Enter the code</h3>
                <p className="mt-2 text-sm text-[#94A3B8]">Enter the current 6-digit code. It refreshes automatically every 30 seconds.</p>
              </div>
            </div>
            <div className="mt-5 rounded-lg border border-[#334155] bg-[#111827] p-4">
              <p className="font-semibold">When you forget your password</p>
              <p className="mt-1 text-sm text-[#94A3B8]">Open <b>Forgot password</b>, enter your account email, the current 6-digit Authenticator code, and your new password.</p>
            </div>
            <div className="mt-5 flex justify-end"><Button onClick={() => setOpen(false)}>Got it</Button></div>
          </div>
        </div>
      ) : null}
    </>
  )
}
