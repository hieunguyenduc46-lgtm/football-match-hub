import { describe, it, expect, beforeEach } from 'vitest'
import { roundLabel } from '../src/utils/roundNames.js'
import { state } from '../src/i18n.js'

describe('roundLabel (English)', () => {
  beforeEach(() => { state.locale = 'en' })

  it.each([
    ['Quarter-finals', 'Quarter-finals'],
    ['Semi-finals', 'Semi-finals'],
    ['Final', 'Final'],
    ['3rd Place Final', '3rd place'],
    ['Round of 16', 'Round of 16'],
    ['Group Stage - 1', 'Group stage · MD 1'],
    ['Group A', 'Group stage A'],
    ['Regular Season - 38', 'Round 38'],
  ])('%s -> %s', (input, expected) => {
    expect(roundLabel(input)).toBe(expected)
  })

  it('hides friendly rounds', () => {
    expect(roundLabel('Friendly International')).toBe('')
  })

  it('returns an empty string for missing input', () => {
    expect(roundLabel(null)).toBe('')
  })

  it('keeps unknown round names unchanged', () => {
    expect(roundLabel('Some Special Stage')).toBe('Some Special Stage')
  })
})

describe('roundLabel (Vietnamese)', () => {
  beforeEach(() => { state.locale = 'vi' })

  it('translates the final and regular season rounds', () => {
    expect(roundLabel('Final')).toBe('Chung kết')
    expect(roundLabel('Regular Season - 5')).toBe('Vòng 5')
  })
})
