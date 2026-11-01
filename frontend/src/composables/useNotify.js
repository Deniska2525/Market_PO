import { useNotificationStore } from '../stores/notifications'
import { describeError } from '../utils/errors'

/**
 * Единая точка уведомлений.
 *
 *   const notify = useNotify()
 *   notify.success('Запись сохранена')            // тост, скрывается сам
 *   notify.fail(error, 'Не удалось сохранить')     // тост с понятным текстом ошибки запроса
 *   await notify.confirm({                          // модальное окно подтверждения
 *     title: 'Удалить запись?', message: '…', danger: true,
 *     action: () => api.delete(...)                 // необязательно: окно покажет «Подождите…»
 *   })                                              // и ошибку внутри, resolve(true) при успехе
 *   await notify.alert({ title, message, tone })    // окно с сообщением
 *   const url = await notify.prompt({ title, inputLabel, validate })  // строка или null
 */
export function useNotify() {
  const store = useNotificationStore()
  const toast = (type, message, options = {}) => store.push({ ...options, type, message })

  return {
    success: (message, options) => toast('success', message, options),
    error: (message, options) => toast('error', message, options),
    warning: (message, options) => toast('warning', message, options),
    info: (message, options) => toast('info', message, options),
    fail: (error, prefix, options) => {
      const text = describeError(error)
      return toast('error', prefix ? `${prefix}: ${text}` : text, options)
    },
    dismiss: id => store.dismiss(id),
    confirm: options => store.openDialog({ ...options, kind: 'confirm' }),
    alert: options => store.openDialog({ ...options, kind: 'alert' }),
    prompt: options => store.openDialog({ ...options, kind: 'prompt' })
  }
}
