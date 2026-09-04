export function fmtPrice(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export function fmtCap(n: number) {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  return fmtPrice(n)
}
