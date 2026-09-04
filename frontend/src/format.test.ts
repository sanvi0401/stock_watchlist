import { describe, expect, it } from 'vitest'
import { fmtCap, fmtPrice } from './utils/format'

describe('formatters', () => {
  it('formats price', () => {
    expect(fmtPrice(172.38)).toContain('172.38')
  })
  it('formats market cap', () => {
    expect(fmtCap(4.23e12)).toBe('$4.23T')
  })
})
