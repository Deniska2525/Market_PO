<template>
  <div
    class="toast"
    :class="toast.type"
    :role="toast.type === 'error' ? 'alert' : 'status'"
    @mouseenter="pause"
    @mouseleave="resume"
    @focusin="pause"
    @focusout="resume"
  >
    <span class="icon" aria-hidden="true"><AppIcon :name="ICONS[toast.type]" :size="14" :stroke-width="3" /></span>
    <div class="body">
      <strong v-if="toast.title" class="title">{{ toast.title }}</strong>
      <span class="message">{{ toast.message }}</span>
    </div>
    <span v-if="toast.count > 1" class="count" :title="`Повторилось ${toast.count} раз`">×{{ toast.count }}</span>
    <button type="button" class="close" aria-label="Закрыть уведомление" @click="emit('close', toast.id)">
      <AppIcon name="x" :size="16" />
    </button>
    <span
      v-if="toast.timeout > 0"
      :key="toast.stamp"
      class="bar"
      :style="{ animationDuration: toast.timeout + 'ms' }"
    ></span>
  </div>
</template>

<script setup>
import AppIcon from './AppIcon.vue'
import { onMounted, onBeforeUnmount, watch } from 'vue'

const ICONS = { success: 'check', error: 'x', warning: 'exclamation', info: 'info-mark' }

const props = defineProps({
  toast: { type: Object, required: true }
})
const emit = defineEmits(['close'])

// Таймер замирает, пока на уведомлении курсор или фокус: текст успевают прочитать
let timer = null
let remaining = props.toast.timeout
let startedAt = 0

function start() {
  if (!(remaining > 0)) return
  clearTimeout(timer)
  startedAt = Date.now()
  timer = setTimeout(() => emit('close', props.toast.id), remaining)
}

function pause() {
  if (!timer) return
  clearTimeout(timer)
  timer = null
  remaining = Math.max(remaining - (Date.now() - startedAt), 800)
}

function resume() {
  if (!timer) start()
}

onMounted(start)
onBeforeUnmount(() => clearTimeout(timer))

// Повтор такого же уведомления перезапускает отсчёт
watch(() => props.toast.stamp, () => {
  clearTimeout(timer)
  timer = null
  remaining = props.toast.timeout
  start()
})
</script>

<style scoped>
.toast {
  --accent: var(--info-text);
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.8rem 2.4rem 0.9rem 0.9rem;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  pointer-events: auto;
}
.toast.success { --accent: var(--success-text); }
.toast.error { --accent: var(--danger-text); }
.toast.warning { --accent: var(--warning-text); }
.toast.info { --accent: var(--info-text); }

.icon {
  flex: 0 0 auto;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 50%;
  background: var(--accent);
  color: var(--bg-card);
  font-size: 0.8rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.1rem;
}
.body { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; word-break: break-word; }
.title { font-size: 0.95rem; }
.message { font-size: 0.92rem; line-height: 1.4; color: var(--text-secondary); }
.title + .message { color: var(--text-secondary); }
.body > .message:only-child { color: var(--text-primary); }
.count { align-self: center; font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); background: var(--bg-tertiary); border-radius: 999px; padding: 0.05rem 0.45rem; }
.close {
  position: absolute;
  top: 0.35rem;
  right: 0.4rem;
  width: 1.7rem;
  height: 1.7rem;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 6px;
  cursor: pointer;
}
.close:hover { background: var(--hover-bg); color: var(--text-primary); }

.bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 3px;
  background: var(--accent);
  opacity: 0.55;
  transform-origin: left;
  animation: toast-bar linear forwards;
}
.toast:hover .bar, .toast:focus-within .bar { animation-play-state: paused; }

@keyframes toast-bar {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}
</style>
