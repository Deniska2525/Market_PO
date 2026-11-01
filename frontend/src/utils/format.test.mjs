// Запуск: cd frontend && node --test src/utils/*.test.mjs
import test from 'node:test'
import assert from 'node:assert/strict'
import {
  extractErrors, formatDate, formatBytes, pluralRu, normalizeTagInput, initials,
  STATUS_LABELS, READINESS_LABELS, INQUIRY_STATUS_LABELS, ROLE_LABELS
} from './format.js'

test('extractErrors: string detail, pydantic list, 429, server error, network failure', () => {
  assert.equal(extractErrors({ response: { status: 403, data: { detail: 'Нет прав' } } }).message, 'Нет прав')
  assert.equal(extractErrors({ response: { status: 422, data: { detail: [{ msg: 'bad' }, { msg: 'worse' }] } } }).message, 'bad; worse')
  assert.match(extractErrors({ response: { status: 429, data: { error: 'Rate limit' } } }).message, /Слишком много/)
  assert.equal(extractErrors({ response: { status: 500, data: {} } }).message, 'Ошибка сервера (500)')
  assert.equal(extractErrors(new Error('x')).message, 'Нет связи с сервером')
  assert.equal(extractErrors(undefined).message, 'Нет связи с сервером')
})

test('formatDate treats zone-less strings as UTC', () => {
  assert.equal(formatDate('2026-10-10T10:00:00'), formatDate('2026-10-10T10:00:00Z'))
  assert.equal(formatDate(null), '—')
  assert.equal(formatDate('garbage'), '—')
})

test('formatBytes', () => {
  assert.equal(formatBytes(0), '0 Б')
  assert.equal(formatBytes(1536), '1.5 КБ')
  assert.equal(formatBytes(5 * 1024 * 1024), '5.0 МБ')
  assert.equal(formatBytes(250 * 1024 * 1024), '250 МБ')
  assert.equal(formatBytes(null), '—')
})

test('pluralRu', () => {
  const f = ['карточка', 'карточки', 'карточек']
  const got = [0, 1, 2, 4, 5, 11, 12, 21, 22, 25, 101, 111].map(n => pluralRu(n, f))
  assert.deepEqual(got, ['карточек', 'карточка', 'карточки', 'карточки', 'карточек', 'карточек', 'карточек', 'карточка', 'карточки', 'карточек', 'карточка', 'карточек'])
})

test('normalizeTagInput matches server-side normalization', () => {
  assert.equal(normalizeTagInput('  Компьютерное   Зрение '), 'компьютерное зрение')
  assert.equal(normalizeTagInput('ЁЖ'), 'еж')
  assert.equal(normalizeTagInput(null), '')
  assert.equal(normalizeTagInput('   '), '')
})

test('initials', () => {
  assert.equal(initials('Иван Петров'), 'ИП')
  assert.equal(initials('admin'), 'A')
  assert.equal(initials(''), '?')
  assert.equal(initials('  мария  сергеевна  иванова'), 'МС')
})

test('label dictionaries cover all statuses the backend uses', () => {
  for (const key of ['draft', 'published']) assert.ok(STATUS_LABELS[key], key)
  for (const key of ['idea', 'prototype', 'pilot', 'ready']) assert.ok(READINESS_LABELS[key], key)
  for (const key of ['new', 'in_progress', 'done']) assert.ok(INQUIRY_STATUS_LABELS[key], key)
  for (const key of ['user', 'admin', 'superuser']) assert.ok(ROLE_LABELS[key], key)
})
