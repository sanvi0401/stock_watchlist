let displayTz = 'America/New_York'

export function setDisplayTimezone(tz: string) {
  if (tz) displayTz = tz
}

export function getDisplayTimezone() {
  return displayTz
}

export function fmtPrice(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export function fmtCap(n: number) {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  return fmtPrice(n)
}

export function fmtWhen(iso: string | null | undefined, tz = displayTz) {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso))
  } catch {
    return new Date(iso).toISOString()
  }
}
