import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { setLocale } from '../src/i18n.js'

// Replace the HTTP client with a mock: no backend or network needed.
vi.mock('../src/services/api.js', () => ({ default: { get: vi.fn() } }))
import api from '../src/services/api.js'
import { useFixturesStore } from '../src/stores/fixtures.js'

const deferred = () => {
  let resolve
  const promise = new Promise((r) => { resolve = r })
  return { promise, resolve }
}

describe('fixtures store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api.get.mockReset()
    setLocale('en')
  })

  it('loads fixtures and clears the loading flag', async () => {
    api.get.mockResolvedValue({ data: { response: [{ fixture: { id: 1 } }] } })
    const store = useFixturesStore()
    await store.fetchFixtures({ date: '2026-10-01' })
    expect(api.get).toHaveBeenCalledWith('/fixtures', { params: { date: '2026-10-01' } })
    expect(store.fixtures).toHaveLength(1)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('shows the error message and empties the list when the request fails', async () => {
    api.get.mockRejectedValue(new Error('Network Error'))
    const store = useFixturesStore()
    store.fixtures = [{ fixture: { id: 9 } }]
    await store.fetchFixtures()
    expect(store.error).toBe('Network Error')
    expect(store.fixtures).toEqual([])
  })

  it('uses the translated fallback message when the error has no message', async () => {
    api.get.mockRejectedValue({})
    const store = useFixturesStore()
    await store.fetchFixtures()
    expect(store.error).toBe('Could not load fixtures')
  })

  it('a failed silent (background) refresh keeps the current list', async () => {
    api.get.mockRejectedValue(new Error('timeout'))
    const store = useFixturesStore()
    store.fixtures = [{ fixture: { id: 9 } }]
    await store.fetchFixtures({}, { silent: true })
    expect(store.fixtures).toHaveLength(1)
  })

  it('ignores a slow old response when a newer request was made (race condition)', async () => {
    const slow = deferred()
    api.get.mockReturnValueOnce(slow.promise)
      .mockResolvedValueOnce({ data: { response: [{ fixture: { id: 2 } }] } })
    const store = useFixturesStore()
    const first = store.fetchFixtures({ date: 'old' })
    await store.fetchFixtures({ date: 'new' })
    slow.resolve({ data: { response: [{ fixture: { id: 1 } }] } })
    await first
    expect(store.fixtures.map((f) => f.fixture.id)).toEqual([2])
  })
})
