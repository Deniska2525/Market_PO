<template>
  <TransitionGroup name="toast" tag="div" class="toast-region" aria-label="Уведомления">
    <ToastItem
      v-for="item in store.toasts"
      :key="item.id"
      :toast="item"
      @close="store.dismiss"
    />
  </TransitionGroup>
</template>

<script setup>
import ToastItem from './ToastItem.vue'
import { useNotificationStore } from '../stores/notifications'

const store = useNotificationStore()
</script>

<style scoped>
.toast-region {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: 3000; /* выше модальных окон (1000) и окон подтверждения (2500) */
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  width: min(400px, calc(100vw - 2rem));
  pointer-events: none; /* пустое пространство между тостами не перехватывает клики */
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.toast-enter-active,
.toast-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.toast-enter-from { opacity: 0; transform: translateY(14px); }
.toast-leave-to { opacity: 0; transform: translateX(28px); }
.toast-move { transition: transform 0.25s ease; }

@media (max-width: 520px) {
  .toast-region { right: 0.5rem; left: 0.5rem; bottom: 0.5rem; width: auto; }
}
</style>
