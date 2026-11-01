<template>
  <div v-if="dialog" class="modal-overlay dlg-overlay" @mousedown.self="onOverlay">
    <div
      ref="panel"
      class="modal-content dlg"
      :class="dialog.tone"
      role="alertdialog"
      aria-modal="true"
      :aria-labelledby="`dlg-title-${dialog.id}`"
      :aria-describedby="dialog.message ? `dlg-msg-${dialog.id}` : undefined"
      tabindex="-1"
    >
      <div class="dlg-icon" aria-hidden="true">{{ TONE_ICONS[dialog.tone] }}</div>
      <h3 :id="`dlg-title-${dialog.id}`">{{ dialog.title }}</h3>
      <p v-if="dialog.message" :id="`dlg-msg-${dialog.id}`" class="dlg-message">{{ dialog.message }}</p>

      <div v-if="dialog.kind === 'prompt'" class="dlg-input">
        <label :for="`dlg-input-${dialog.id}`">{{ dialog.inputLabel }}</label>
        <input
          :id="`dlg-input-${dialog.id}`"
          ref="inputEl"
          type="text"
          :value="dialog.inputValue"
          :placeholder="dialog.inputPlaceholder"
          :disabled="dialog.busy"
          @input="store.setDialogValue($event.target.value)"
          @keydown.enter.prevent="store.confirmDialog()"
        >
      </div>

      <p v-if="dialog.irreversible" class="dlg-warning">Это действие нельзя отменить.</p>
      <p v-if="dialog.error" class="dlg-error" role="alert">{{ dialog.error }}</p>

      <div class="dlg-actions">
        <button
          v-if="dialog.kind !== 'alert'"
          ref="cancelBtn"
          type="button"
          class="btn btn-secondary"
          :disabled="dialog.busy"
          @click="store.cancelDialog()"
        >{{ dialog.cancelText }}</button>
        <button
          ref="okBtn"
          type="button"
          class="btn"
          :class="dialog.danger ? 'btn-danger' : 'btn-primary'"
          :disabled="dialog.busy"
          @click="store.confirmDialog()"
        >{{ dialog.busy ? 'Подождите…' : dialog.confirmText }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useNotificationStore } from '../stores/notifications'
import { useDialogA11y } from '../composables/useDialogA11y'

const TONE_ICONS = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '⛔' }

const store = useNotificationStore()
const dialog = computed(() => store.dialog)

const panel = ref(null)
const cancelBtn = ref(null)
const okBtn = ref(null)
const inputEl = ref(null)

function onOverlay() {
  if (dialog.value && !dialog.value.persistent) store.cancelDialog()
}

// Фокус: в поле ввода; у опасного действия — на «Отмена», чтобы случайный Enter ничего не удалил
useDialogA11y({
  panel,
  active: computed(() => store.dialog?.id ?? 0),
  onEscape: () => store.cancelDialog(),
  initialFocus: () => {
    const d = store.dialog
    if (!d) return null
    if (d.kind === 'prompt') return inputEl.value
    if (d.kind === 'confirm' && d.danger) return cancelBtn.value
    return okBtn.value
  }
})
</script>

<style scoped>
.dlg-overlay { z-index: 2500; }
.dlg { text-align: center; max-width: 440px; }
.dlg-icon { font-size: 2.4rem; margin-bottom: 0.4rem; }
.dlg h3 { margin-bottom: 0.6rem; }
.dlg-message { color: var(--text-secondary); line-height: 1.5; white-space: pre-line; word-break: break-word; }
.dlg-warning { margin-top: 0.7rem; color: var(--danger-text); font-weight: 600; font-size: 0.9rem; }
.dlg-error { margin-top: 0.8rem; padding: 0.6rem 0.8rem; background: var(--danger-bg); color: var(--danger-text); border-radius: 8px; font-size: 0.9rem; text-align: left; }
.dlg-input { margin-top: 1rem; text-align: left; }
.dlg-input label { display: block; margin-bottom: 0.3rem; color: var(--text-secondary); font-size: 0.9rem; }
.dlg-input input { width: 100%; padding: 0.65rem 0.8rem; border: 1px solid var(--input-border); border-radius: 8px; background: var(--input-bg); color: var(--text-primary); }
.dlg-actions { display: flex; gap: 0.6rem; justify-content: center; margin-top: 1.4rem; flex-wrap: wrap; }
</style>
