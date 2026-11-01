// Логика очереди уведомлений (тостов) без Vue — проверяется через `node --test`.
export const TOAST_TYPES = ['success', 'error', 'warning', 'info']
// Сколько миллисекунд показывать; 0 — не скрывать само (закрывается кнопкой)
export const DEFAULT_TIMEOUT = { success: 4000, info: 5000, warning: 7000, error: 9000 }
export const MAX_TOASTS = 5
const MAX_MESSAGE = 400
const MAX_TITLE = 100

let sequence = 0

export function normalizeToast(input) {
  const type = TOAST_TYPES.includes(input?.type) ? input.type : 'info'
  const message = String(input?.message ?? '').trim().slice(0, MAX_MESSAGE)
  const title = input?.title ? String(input.title).trim().slice(0, MAX_TITLE) : ''
  const timeout = Number.isFinite(input?.timeout) && input.timeout >= 0 ? input.timeout : DEFAULT_TIMEOUT[type]
  return { type, message, title, timeout }
}

// Возвращает новый список. Одинаковое уведомление не дублируется, а получает счётчик
// и перезапускает таймер (stamp). Сверх лимита вытесняются самые старые из тех, что
// скрываются сами; «липкие» (timeout 0) остаются, пока их не закроют.
export function pushToast(list, input, max = MAX_TOASTS) {
  const base = normalizeToast(input)
  if (!base.message && !base.title) return list

  const same = list.findIndex(t => t.type === base.type && t.message === base.message && t.title === base.title)
  let next
  if (same >= 0) {
    next = list.slice()
    next[same] = { ...list[same], timeout: base.timeout, count: list[same].count + 1, stamp: list[same].stamp + 1 }
  } else {
    sequence += 1
    next = [...list, { ...base, id: sequence, count: 1, stamp: 0 }]
  }

  while (next.length > max) {
    const victim = next.findIndex((t, i) => t.timeout > 0 && i < next.length - 1)
    next.splice(victim >= 0 ? victim : 0, 1)
  }
  return next
}

export function removeToast(list, id) {
  return list.filter(t => t.id !== id)
}
