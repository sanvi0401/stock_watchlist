import { describe, expect, it } from 'vitest'
import { TERMS_OF_SERVICE, PRIVACY_POLICY } from './legal'
import { fmtCap, fmtPrice, fmtWhen, setDisplayTimezone } from './utils/format'

describe('formatters', () => {
  it('formats price', () => {
    expect(fmtPrice(172.38)).toContain('172.38')
  })
  it('formats market cap', () => {
    expect(fmtCap(4.23e12)).toBe('$4.23T')
  })
})

describe('timezone formatting', () => {
  it('formats an ISO timestamp in the selected zone', () => {
    setDisplayTimezone('UTC')
    const out = fmtWhen('2026-09-04T16:00:00Z')
    expect(out).toMatch(/2026/)
    expect(out).not.toBe('—')
  })
})

describe('legal copy', () => {
  it('has readable terms and privacy', () => {
    expect(TERMS_OF_SERVICE).toContain('not investment')
    expect(PRIVACY_POLICY).toContain('We do not sell your personal data')
  })
})
