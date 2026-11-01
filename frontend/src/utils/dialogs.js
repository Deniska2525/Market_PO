// Описание модальных окон (подтверждение, сообщение, ввод) без Vue.
export const DIALOG_KINDS = ['confirm', 'alert', 'prompt']
export const DIALOG_TONES = ['info', 'success', 'warning', 'error']

export function normalizeDialog(options = {}) {
  const kind = DIALOG_KINDS.includes(options.kind) ? options.kind : 'confirm'
  const danger = !!options.danger
  const tone = DIALOG_TONES.includes(options.tone) ? options.tone : (danger ? 'warning' : 'info')

  const defaultConfirm = kind === 'confirm' ? (danger ? 'Удалить' : 'Подтвердить') : (kind === 'prompt' ? 'Готово' : 'Понятно')
  return {
    kind,
    title: String(options.title || (kind === 'confirm' ? 'Подтвердите действие' : 'Сообщение')).slice(0, 120),
    message: String(options.message || '').slice(0, 1000),
    confirmText: options.confirmText || defaultConfirm,
    cancelText: options.cancelText || 'Отмена',
    danger,
    tone,
    irreversible: options.irreversible ?? danger, // показывать «нельзя отменить»
    persistent: !!options.persistent, // не закрывать по клику мимо окна
    inputLabel: options.inputLabel || '',
    inputPlaceholder: options.inputPlaceholder || '',
    inputValue: options.inputValue ? String(options.inputValue) : ''
  }
}

// Куда перейдёт фокус по Tab / Shift+Tab, чтобы он не уходил за пределы окна
export function nextFocusIndex(current, total, backwards) {
  if (total <= 0) return -1
  if (current < 0) return backwards ? total - 1 : 0
  return backwards ? (current - 1 + total) % total : (current + 1) % total
}
