<template>
  <button
    type="button"
    class="theme-toggle"
    :class="{ active: themeStore.isDark }"
    role="switch"
    :aria-checked="themeStore.isDark"
    :aria-label="themeStore.isDark ? 'Включить светлую тему' : 'Включить тёмную тему'"
    :title="themeStore.isDark ? 'Светлая тема' : 'Тёмная тема'"
    @click="themeStore.toggleTheme"
  >
    <span class="toggle-knob">
      <!-- Солнце: видно в светлой теме -->
      <svg class="icon icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </svg>
      <!-- Луна: видно в тёмной теме -->
      <svg class="icon icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    </span>
  </button>
</template>

<script setup>
import { useThemeStore } from '../stores/theme'

const themeStore = useThemeStore()
</script>

<style scoped>
.theme-toggle {
  position: relative;
  flex-shrink: 0;
  width: 64px;
  height: 32px;
  padding: 0;
  border-radius: 999px;
  background: var(--toggle-bg);
  border: 2px solid var(--primary-color);
  cursor: pointer;
  transition: background 0.3s ease, border-color 0.3s ease, transform 0.2s ease;
}

.theme-toggle:hover {
  transform: scale(1.04);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 3px;
}

/* Ручка с иконкой внутри */
.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--toggle-knob);
  color: #0f172a; /* тёмная иконка читается на зелёной и на светлой ручке */
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: transform 0.3s ease, background 0.3s ease;
}

.theme-toggle.active .toggle-knob {
  transform: translateX(32px);
  background: var(--toggle-knob-active);
}

/* Обе иконки лежат друг на друге, показывается одна */
.icon {
  position: absolute;
  width: 14px;
  height: 14px;
  transition: opacity 0.25s ease, transform 0.35s ease;
}

.icon-sun {
  opacity: 1;
  transform: rotate(0deg) scale(1);
}

.icon-moon {
  opacity: 0;
  transform: rotate(-90deg) scale(0.6);
}

.theme-toggle.active .icon-sun {
  opacity: 0;
  transform: rotate(90deg) scale(0.6);
}

.theme-toggle.active .icon-moon {
  opacity: 1;
  transform: rotate(0deg) scale(1);
}

@media (prefers-reduced-motion: reduce) {
  .theme-toggle,
  .toggle-knob,
  .icon {
    transition: none;
  }
}
</style>
