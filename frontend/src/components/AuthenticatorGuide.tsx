import { useState } from 'react'
import { Button } from './ui'

export default function AuthenticatorGuide() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>
        How to use Authenticator
      </Button>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-labelledby="auth-guide-title">
          <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-xl border border-[#334155] bg-[#0F172A] p-4 shadow-2xl sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#94A3B8]">Account security</p>
                <h2 id="auth-guide-title" className="mt-1 text-2xl font-semibold">How to use Google Authenticator</h2>
                <p className="mt-2 text-sm text-[#94A3B8]">Follow the visual guide below to set up Authenticator and use your 6-digit code.</p>
              </div>
              <button className="shrink-0 text-2xl leading-none text-[#94A3B8] hover:text-white" onClick={() => setOpen(false)} aria-label="Close guide">×</button>
            </div>
            <div className="mt-5 overflow-hidden rounded-lg border border-[#232F46] bg-[#080F1B]">
              <img src="/authenticator.png" alt="How to use Google Authenticator step-by-step guide" className="mx-auto block h-auto w-full" />
            </div>
            <div className="mt-5 rounded-lg border border-[#334155] bg-[#111827] p-4">
              <p className="font-semibold">Using your code</p>
              <p className="mt-1 text-sm text-[#94A3B8]">Open Google Authenticator, use the current 6-digit code shown for your account, and enter it where Market Watch asks for the code.</p>
            </div>
            <div className="mt-5 flex justify-end"><Button onClick={() => setOpen(false)}>Got it</Button></div>
          </div>
        </div>
      ) : null}
    </>
  )
}
