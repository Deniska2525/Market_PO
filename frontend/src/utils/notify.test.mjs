// Запуск: cd frontend && node --test src/utils/notify.test.mjs
import test from 'node:test'
import assert from 'node:assert/strict'
import { pushToast, removeToast, normalizeToast, DEFAULT_TIMEOUT, MAX_TOASTS } from './toasts.js'
import { normalizeDialog, nextFocusIndex } from './dialogs.js'
import { describeError } from './errors.js'

test('normalizeToast: type fallback, trimming, default timeouts, explicit 0', () => {
  assert.equal(normalizeToast({ type: 'weird', message: ' hi ' }).type, 'info')
  assert.equal(normalizeToast({ type: 'error', message: 'x' }).timeout, DEFAULT_TIMEOUT.error)
  assert.equal(normalizeToast({ type: 'success', message: 'x' }).timeout, DEFAULT_TIMEOUT.success)
  assert.equal(normalizeToast({ type: 'error', message: 'x', timeout: 0 }).timeout, 0)
  assert.equal(normalizeToast({ type: 'error', message: 'x', timeout: -5 }).timeout, DEFAULT_TIMEOUT.error)
  assert.equal(normalizeToast({ message: 'a'.repeat(1000) }).message.length, 400)
  assert.equal(normalizeToast({ message: 'm', title: '  T ' }).title, 'T')
})

test('pushToast: adds with unique ids; empty messages are ignored', () => {
  let list = []
  list = pushToast(list, { type: 'success', message: 'one' })
  list = pushToast(list, { type: 'success', message: 'two' })
  assert.equal(list.length, 2)
  assert.notEqual(list[0].id, list[1].id)
  assert.equal(pushToast(list, { type: 'info', message: '   ' }), list)
})

test('pushToast: identical toast increments count and restarts timer instead of stacking', () => {
  let list = pushToast([], { type: 'error', message: 'fail' })
  const first = list[0]
  list = pushToast(list, { type: 'error', message: 'fail' })
  assert.equal(list.length, 1)
  assert.equal(list[0].id, first.id)
  assert.equal(list[0].count, 2)
  assert.equal(list[0].stamp, first.stamp + 1)
  list = pushToast(list, { type: 'success', message: 'fail' }) // другой тип — другое уведомление
  assert.equal(list.length, 2)
})

test('pushToast: limit evicts oldest auto-dismiss toasts, keeps sticky ones and the newest', () => {
  let list = pushToast([], { type: 'error', message: 'sticky', timeout: 0 })
  for (let i = 0; i < MAX_TOASTS + 2; i++) list = pushToast(list, { type: 'info', message: `n${i}` })
  assert.equal(list.length, MAX_TOASTS)
  assert.ok(list.some(t => t.message === 'sticky'))
  assert.equal(list[list.length - 1].message, `n${MAX_TOASTS + 1}`)
  assert.ok(!list.some(t => t.message === 'n0'))
})

test('pushToast: when everything is sticky the oldest goes, newest stays', () => {
  let list = []
  for (let i = 0; i < 3; i++) list = pushToast(list, { type: 'error', message: `s${i}`, timeout: 0 }, 2)
  assert.deepEqual(list.map(t => t.message), ['s1', 's2'])
})

test('removeToast', () => {
  const list = pushToast(pushToast([], { message: 'a' }), { message: 'b' })
  assert.deepEqual(removeToast(list, list[0].id).map(t => t.message), ['b'])
  assert.equal(removeToast(list, 99999).length, 2)
})

test('normalizeDialog defaults by kind', () => {
  const del = normalizeDialog({ kind: 'confirm', danger: true })
  assert.equal(del.confirmText, 'Удалить')
  assert.equal(del.tone, 'warning')
  assert.equal(del.irreversible, true)
  const ok = normalizeDialog({ kind: 'confirm' })
  assert.equal(ok.confirmText, 'Подтвердить')
  assert.equal(ok.irreversible, false)
  assert.equal(normalizeDialog({ kind: 'alert' }).confirmText, 'Понятно')
  assert.equal(normalizeDialog({ kind: 'prompt' }).confirmText, 'Готово')
  assert.equal(normalizeDialog({ kind: 'nope' }).kind, 'confirm')
  assert.equal(normalizeDialog({ kind: 'alert', tone: 'error' }).tone, 'error')
  assert.equal(normalizeDialog({ kind: 'confirm', danger: true, irreversible: false }).irreversible, false)
})

test('nextFocusIndex wraps in both directions and handles focus outside', () => {
  assert.equal(nextFocusIndex(2, 3, false), 0)
  assert.equal(nextFocusIndex(0, 3, true), 2)
  assert.equal(nextFocusIndex(1, 3, false), 2)
  assert.equal(nextFocusIndex(-1, 3, false), 0)
  assert.equal(nextFocusIndex(-1, 3, true), 2)
  assert.equal(nextFocusIndex(0, 0, false), -1)
})

test('describeError: server detail, network failure, plain Error, fallback', () => {
  assert.equal(describeError({ isAxiosError: true, response: { status: 403, data: { detail: 'Нет прав' } } }), 'Нет прав')
  assert.equal(describeError({ isAxiosError: true }), 'Нет связи с сервером')
  assert.equal(describeError(new Error('своя ошибка')), 'своя ошибка')
  assert.equal(describeError(null), 'Не удалось выполнить действие')
  assert.equal(describeError('x', 'запасной'), 'запасной')
})
