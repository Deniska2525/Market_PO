import { defineStore } from 'pinia'
import { pushToast, removeToast } from '../utils/toasts'
import { normalizeDialog } from '../utils/dialogs'
import { describeError } from '../utils/errors'

// Функции (resolve, action, validate) в реактивное состояние не кладём
const handlers = new Map()
const queue = []
let dialogSequence = 0

export const useNotificationStore = defineStore('notifications', {
  state: () => ({
    toasts: [],
    dialog: null // активное модальное окно; остальные ждут в очереди
  }),

  actions: {
    push(input) {
      this.toasts = pushToast(this.toasts, input)
    },
    dismiss(id) {
      this.toasts = removeToast(this.toasts, id)
    },
    clearToasts() {
      this.toasts = []
    },

    // Возвращает Promise: confirm -> true/false, alert -> undefined, prompt -> строка или null
    openDialog(options) {
      return new Promise(resolve => {
        queue.push({ options, resolve })
        this._showNext()
      })
    },

    _showNext() {
      if (this.dialog || !queue.length) return
      const { options, resolve } = queue.shift()
      dialogSequence += 1
      handlers.set(dialogSequence, { resolve, action: options.action, validate: options.validate })
      this.dialog = { id: dialogSequence, ...normalizeDialog(options), busy: false, error: '' }
    },

    _finish(result) {
      const current = this.dialog
      if (!current) return
      const entry = handlers.get(current.id)
      handlers.delete(current.id)
      this.dialog = null
      entry?.resolve(result)
      this._showNext()
    },

    setDialogValue(value) {
      if (!this.dialog) return
      this.dialog.inputValue = value
      this.dialog.error = ''
    },

    async confirmDialog() {
      const current = this.dialog
      if (!current || current.busy) return
      const entry = handlers.get(current.id) || {}

      if (current.kind === 'prompt') {
        const value = current.inputValue.trim()
        const problem = entry.validate ? entry.validate(value) : ''
        if (problem) {
          current.error = problem
          return
        }
        this._finish(value)
        return
      }

      // confirm с action: окно остаётся открытым, пока выполняется запрос;
      // при ошибке показывает её внутри и даёт повторить или отменить
      if (current.kind === 'confirm' && entry.action) {
        current.busy = true
        current.error = ''
        try {
          await entry.action()
        } catch (error) {
          if (this.dialog && this.dialog.id === current.id) {
            this.dialog.busy = false
            this.dialog.error = describeError(error)
          }
          return
        }
        this._finish(true)
        return
      }

      this._finish(current.kind === 'confirm' ? true : undefined)
    },

    cancelDialog() {
      const current = this.dialog
      if (!current || current.busy) return
      this._finish(current.kind === 'confirm' ? false : (current.kind === 'prompt' ? null : undefined))
    }
  }
})
