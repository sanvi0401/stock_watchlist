const LOCALE: Record<string, string> = { INR: 'en-IN', GBP: 'en-GB', EUR: 'de-DE', JPY: 'ja-JP', HKD: 'en-HK', CAD: 'en-CA', AUD: 'en-AU' }

/** Price in the instrument's own currency: ₹1,322.00 for NSE, $172.38 for Nasdaq, £1.26 for LSE. */
export function fmtPrice(n: number, currency = 'USD') {
  const code = currency || 'USD'
  try {
    return n.toLocaleString(LOCALE[code] ?? 'en-US', { style: 'currency', currency: code, maximumFractionDigits: code === 'JPY' ? 0 : 2 })
  } catch {
    return `${n.toFixed(2)} ${code}`
  }
}

export function fmtCap(n: number, currency = 'USD') {
  if (!n) return '—'
  const sym = symbolFor(currency)
  if (currency === 'INR') {
    if (n >= 1e12) return `${sym}${(n / 1e12).toFixed(2)} L Cr`
    if (n >= 1e7) return `${sym}${(n / 1e7).toFixed(0)} Cr`
  }
  if (n >= 1e12) return `${sym}${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `${sym}${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `${sym}${(n / 1e6).toFixed(1)}M`
  return fmtPrice(n, currency)
}

function symbolFor(currency: string) {
  try {
    return (0).toLocaleString(LOCALE[currency] ?? 'en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).replace(/[\d.,\s]/g, '')
  } catch {
    return `${currency} `
  }
}

export function fmtVolume(n: number) {
  if (!n) return '—'
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`
  return String(Math.round(n))
}

/** "3 minutes ago", "yesterday", … relative to `now` (injectable for tests). */
export function fmtRelative(iso: string | null | undefined, now: Date = new Date()) {
  if (!iso) return '—'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return '—'
  const diff = Math.max(0, now.getTime() - then)
  const min = Math.round(diff / 60000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min} min ago`
  const hours = Math.round(min / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.round(hours / 24)
  if (days === 1) return 'yesterday'
  if (days < 30) return `${days} days ago`
  return new Date(iso).toLocaleDateString()
}

export function fmtDateTime(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString()
}

export const MARKET_LABEL: Record<string, string> = {
  OPEN: 'open',
  CLOSED: 'closed',
  PRE_MARKET: 'pre-market',
}

export function marketLine(markets: { exchange_name: string; state: string }[]) {
  if (!markets.length) return ''
  return markets.map((m) => `${m.exchange_name} ${MARKET_LABEL[m.state] ?? m.state.toLowerCase()}`).join(' · ')
}
