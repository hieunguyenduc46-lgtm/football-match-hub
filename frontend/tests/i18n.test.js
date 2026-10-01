import { describe, it, expect, afterEach } from 'vitest'
import { messages, state, setLocale, t } from '../src/i18n.js'

describe('translation dictionary', () => {
  it('Vietnamese and English have exactly the same keys (no missing translations)', () => {
    const vi = Object.keys(messages.vi).sort()
    const en = Object.keys(messages.en).sort()
    expect(en).toEqual(vi)
  })

  it('has no empty translations', () => {
    for (const lang of ['vi', 'en']) {
      for (const [key, value] of Object.entries(messages[lang])) {
        expect(value, `${lang}.${key}`).toBeTruthy()
      }
    }
  })

  it('contains the UI strings moved out of the components', () => {
    for (const key of ['switchLang', 'comparePlayers', 'themeLight', 'themeDark', 'searchBoxPh',
      'secCountries', 'secLeagues', 'wordLeagues', 'noMatchesShort', 'loadMatchErr', 'loadFixturesErr']) {
      expect(messages.en[key], key).toBeTruthy()
    }
  })
})

describe('t() and setLocale()', () => {
  afterEach(() => setLocale('vi'))

  it('returns the Vietnamese text in vi mode', () => {
    setLocale('vi')
    expect(t('comparePlayers')).toBe('So sánh cầu thủ')
  })

  it('switches to English after setLocale("en")', () => {
    setLocale('en')
    expect(state.locale).toBe('en')
    expect(t('comparePlayers')).toBe('Compare players')
    expect(t('loadFixturesErr')).toBe('Could not load fixtures')
  })

  it('falls back to Vietnamese when a key is missing in English', () => {
    messages.vi.__testOnlyKey = 'chỉ có tiếng Việt'
    setLocale('en')
    expect(t('__testOnlyKey')).toBe('chỉ có tiếng Việt')
    delete messages.vi.__testOnlyKey
  })

  it('returns the key itself when it does not exist at all', () => {
    expect(t('no.such.key')).toBe('no.such.key')
  })
})
