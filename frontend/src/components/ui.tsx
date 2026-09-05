import type { ReactNode } from 'react'
import type { DataStatus, Severity } from '../types'
import { cn } from '../utils/cn'
export { cn } from '../utils/cn'
export { fmtCap, fmtPrice } from '../utils/format'

export function Button({
  children,
  variant = 'primary',
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'outline' | 'ghost' }) {
  const styles = {
    primary: 'bg-intel text-white hover:bg-[#4f46e5]',
    outline: 'border border-[#232F46] text-[#CBD5E1] hover:bg-[#1A2234] hover:border-[#2E3E5B] hover:text-[#F8FAFC]',
    ghost: 'text-[#94A3B8] hover:bg-[#1A2234] hover:text-[#F8FAFC]',
  }[variant]
  return (
    <button
      className={cn('inline-flex items-center justify-center gap-2 rounded px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50', styles, className)}
      {...props}
    >
      {children}
    </button>
  )
}

export function Card({ children, className, accent }: { children: ReactNode; className?: string; accent?: string }) {
  return (
    <div
      className={cn('rounded-lg border border-[#232F46] bg-[#111726] p-4', className)}
      style={accent ? { borderLeft: `2px solid ${accent}` } : undefined}
    >
      {children}
    </div>
  )
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        'h-9 w-full rounded border border-[#232F46] bg-[#0B0F17] px-3 text-sm text-[#F8FAFC] placeholder:text-[#94A3B8] outline-none focus:border-intel focus:ring-1 focus:ring-intel',
        props.className,
      )}
    />
  )
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.06em] text-[#94A3B8]">{children}</label>
}

export function Delta({ value }: { value: number | null | undefined }) {
  if (value == null || Number.isNaN(value)) return <span className="font-mono text-[#94A3B8]">—</span>
  const up = value >= 0
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-mono', up ? 'bg-gain/10 text-gain border border-gain/25' : 'bg-loss/10 text-loss border border-loss/25')}>
      {up ? '▲' : '▼'} {Math.abs(value).toFixed(2)}%
    </span>
  )
}

export function SeverityPill({ severity }: { severity: Severity }) {
  const map = {
    HIGH: 'bg-loss/10 text-loss border-loss/25',
    MEANINGFUL: 'bg-warn/10 text-warn border-warn/30',
    NOTABLE: 'bg-intel/15 text-[#818CF8] border-intel/30',
    STABLE: 'bg-gain/10 text-gain border-gain/25',
  }
  const label = { HIGH: 'High significance', MEANINGFUL: 'Meaningful', NOTABLE: 'Notable', STABLE: 'Stable' }[severity]
  return <span className={cn('rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider', map[severity])}>{label}</span>
}

export function DataBadge({ status }: { status: DataStatus | string }) {
  const map: Record<string, string> = {
    LIVE: 'text-gain',
    DELAYED: 'text-warn',
    STALE: 'text-warn',
    UNAVAILABLE: 'text-loss',
  }
  return <span className={cn('font-mono text-[11px] uppercase tracking-wider', map[status] || 'text-outline')}>{status}</span>
}

export function ExchangeTag({ name, state }: { name: string; state?: string }) {
  if (!name) return null
  const dot = state === 'OPEN' ? 'bg-gain' : state === 'PRE_MARKET' ? 'bg-warn' : 'bg-[#64748B]'
  return (
    <span className="inline-flex items-center gap-1 rounded border border-[#232F46] px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-[#94A3B8]" title={state ? `${name} ${state.toLowerCase().replace('_', ' ')}` : name}>
      {state ? <span className={cn('h-1.5 w-1.5 rounded-full', dot)} /> : null}
      {name}
    </span>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-surface-container-high', className)} />
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <Card className="text-center py-12">
      <h2 className="text-lg font-semibold text-on-surface">{title}</h2>
      <p className="mt-2 text-sm text-[#94A3B8]">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </Card>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <Card className="border-loss/40" accent="#F43F5E">
      <p className="text-sm text-loss">{message}</p>
    </Card>
  )
}

export function Modal({ open, title, children, onClose, wide }: { open: boolean; title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/65 p-4" onClick={onClose}>
      <div
        className={cn(
          'w-full rounded-xl border border-[#2E3E5B] bg-[#1A2234] p-5 shadow-[0_16px_32px_-8px_rgba(0,0,0,0.65)]',
          wide ? 'max-w-2xl' : 'max-w-lg',
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} className="text-outline hover:text-on-surface">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}
