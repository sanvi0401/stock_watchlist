import { describe, expect, it } from 'vitest'
import { PRIVACY_POLICY, TERMS_OF_SERVICE } from './legal'
import { fmtCap, fmtPrice, fmtRelative, fmtVolume, marketLine } from './utils/format'

describe('formatters', () => {
  it('formats price in the instrument currency', () => {
    expect(fmtPrice(172.38)).toBe('$172.38')
    expect(fmtPrice(1322, 'INR')).toBe('₹1,322.00')
    expect(fmtPrice(1.256, 'GBP')).toBe('£1.26')
    expect(fmtPrice(3081, 'JPY')).toBe('￥3,081')
    expect(fmtPrice(5, 'XXX')).toMatch(/5/)
  })
  it('summarises markets', () => {
    expect(marketLine([{ exchange_name: 'NSE', state: 'OPEN' }, { exchange_name: 'NYSE', state: 'CLOSED' }])).toBe('NSE open · NYSE closed')
    expect(marketLine([])).toBe('')
  })
  it('formats market cap and volume', () => {
    expect(fmtCap(4.23e12)).toBe('$4.23T')
    expect(fmtCap(1.79e13, 'INR')).toBe('₹17.90 L Cr')
    expect(fmtCap(0)).toBe('—')
    expect(fmtVolume(89_400_000)).toBe('89.4M')
    expect(fmtVolume(1_800)).toBe('2K')
  })
  it('formats relative time', () => {
    const now = new Date('2026-09-04T12:00:00Z')
    expect(fmtRelative('2026-09-04T11:59:40Z', now)).toBe('just now')
    expect(fmtRelative('2026-09-04T11:45:00Z', now)).toBe('15 min ago')
    expect(fmtRelative('2026-09-04T09:00:00Z', now)).toBe('3 hours ago')
    expect(fmtRelative('2026-09-03T12:00:00Z', now)).toBe('yesterday')
    expect(fmtRelative(null, now)).toBe('—')
    expect(fmtRelative('garbage', now)).toBe('—')
  })
})

describe('legal copy', () => {
  it('states this is not investment advice', () => {
    expect(TERMS_OF_SERVICE).toContain('not investment')
    expect(PRIVACY_POLICY).toContain('We do not sell your personal data')
  })
})
