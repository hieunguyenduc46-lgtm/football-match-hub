import { describe, it, expect } from 'vitest'
import {
  isLive, isFinished, isOff, isPostponed, isCancelled, isBreak, breakStatusKey,
  isStaleLive, isLiveFixture,
} from '../src/utils/format.js'

// Build a fixture that kicked off `minsAgo` minutes ago with the given status.
const fixture = (short, minsAgo) => ({
  fixture: { status: { short }, timestamp: Math.floor(Date.now() / 1000) - minsAgo * 60 },
})

describe('match status helpers', () => {
  it('detects live statuses', () => {
    expect(isLive('1H')).toBe(true)
    expect(isLive('2H')).toBe(true)
    expect(isLive('FT')).toBe(false)
  })

  it('detects finished statuses', () => {
    expect(isFinished('FT')).toBe(true)
    expect(isFinished('PEN')).toBe(true)
    expect(isFinished('NS')).toBe(false)
  })

  it('treats postponed and cancelled matches as "off"', () => {
    expect(isPostponed('PST')).toBe(true)
    expect(isCancelled('CANC')).toBe(true)
    expect(isOff('PST')).toBe(true)
    expect(isOff('ABD')).toBe(true)
    expect(isOff('NS')).toBe(false)
  })

  it('maps break statuses to the right label key', () => {
    expect(isBreak('HT')).toBe(true)
    expect(breakStatusKey('HT')).toBe('halftime')
    expect(breakStatusKey('BT')).toBe('breakTime')
    expect(breakStatusKey('P')).toBe('penalties')
  })
})

describe('stale live detection', () => {
  it('a second half that started recently is really live', () => {
    const fx = fixture('2H', 70)
    expect(isStaleLive(fx)).toBe(false)
    expect(isLiveFixture(fx)).toBe(true)
  })

  it('a match stuck in 2H for 5 hours is stale, not live', () => {
    const fx = fixture('2H', 300)
    expect(isStaleLive(fx)).toBe(true)
    expect(isLiveFixture(fx)).toBe(false)
  })

  it('a finished match is never stale live', () => {
    expect(isStaleLive(fixture('FT', 300))).toBe(false)
  })
})
