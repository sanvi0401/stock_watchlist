import { describe, expect, it } from 'vitest'
import { PRIVACY_POLICY, TERMS_OF_SERVICE } from './legal'
import { fmtCap, fmtPrice, fmtRelative, fmtVolume } from './utils/format'

describe('formatters', () => {
  it('formats price', () => {
    expect(fmtPrice(172.38)).toContain('172.38')
  })
  it('formats market cap and volume', () => {
    expect(fmtCap(4.23e12)).toBe('$4.23T')
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
