import { describe, it, expect } from 'vitest'
import { isNational, isFriendly, passPct, splitStats, aggregateOfficial } from '../src/utils/playerStats.js'

const entry = (team, league, goals, apps = 10) => ({
  team: { id: team.length, name: team },
  league: { id: league.length, name: league },
  goals: { total: goals, assists: 0 },
  games: { appearences: apps, rating: '7.0' },
})

describe('competition classification', () => {
  it('a team named after the player nationality is the national team', () => {
    expect(isNational(entry('France', 'UEFA Nations League', 1), 'France')).toBe(true)
  })

  it('Europa League is a club competition, not national team', () => {
    expect(isNational(entry('Roma', 'UEFA Europa League', 1), 'Italy')).toBe(false)
  })

  it('detects friendlies', () => {
    expect(isFriendly(entry('Argentina', 'Friendlies', 1))).toBe(true)
    expect(isFriendly(entry('Inter Miami', 'Major League Soccer', 1))).toBe(false)
  })
})

describe('passPct', () => {
  it('keeps a normal percentage', () => expect(passPct('85', 10)).toBe(85))
  it('divides a summed percentage by appearances', () => expect(passPct('850', 10)).toBe(85))
  it('returns null for missing values', () => expect(passPct(null, 10)).toBeNull())
})

describe('official totals', () => {
  const player = {
    player: { nationality: 'Argentina' },
    statistics: [
      entry('Inter Miami', 'Major League Soccer', 20, 25),
      entry('Argentina', 'World Cup - Qualification South America', 5, 6),
      entry('Argentina', 'Friendlies', 3, 2),
    ],
  }

  it('splits club and national team stats and drops friendlies', () => {
    const { club, national } = splitStats(player)
    expect(club.map(r => r.team)).toEqual(['Inter Miami'])
    expect(national.map(r => r.goals)).toEqual([5])
  })

  it('official total = club + national team, without friendlies', () => {
    expect(aggregateOfficial(player).goals).toBe(25)
  })

  it('returns null when there are no stats', () => {
    expect(aggregateOfficial({ statistics: [] })).toBeNull()
  })
})
