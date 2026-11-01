<template>
  <div class="user-menu" ref="menuRef">
    <button class="user-trigger" @click="toggle" :aria-expanded="isOpen" aria-haspopup="menu">
      <span class="user-avatar">{{ initials }}</span>
      <span class="user-name">{{ displayName }}</span>
      <span class="arrow" :class="{ open: isOpen }">▼</span>
    </button>

    <div v-if="isOpen" class="dropdown" role="menu">
      <div class="welcome">
        {{ authStore.welcomeMessage }}
        <small v-if="authStore.facultyName" class="faculty-note">{{ authStore.facultyName }}</small>
      </div>
      <template v-if="authStore.isStaff">
        <router-link to="/manage" class="dropdown-item" @click="close">🗂️ Карточки</router-link>
        <router-link to="/manage/inquiries" class="dropdown-item" @click="close">📨 Заявки</router-link>
      </template>
      <router-link v-if="authStore.isSuperuser" to="/admin" class="dropdown-item" @click="close">⚙️ Администрирование</router-link>
      <router-link to="/profile" class="dropdown-item" @click="close">📝 Редактировать профиль</router-link>
      <button class="dropdown-item logout" @click="handleLogout">🚪 Выйти</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['logout'])

const authStore = useAuthStore()
const isOpen = ref(false)
const menuRef = ref(null)

const initials = computed(() => {
  const name = authStore.user?.full_name || authStore.user?.username || 'U'
  return name.slice(0, 2).toUpperCase()
})

const displayName = computed(() => {
  return authStore.user?.full_name || authStore.user?.username
})

const toggle = () => { isOpen.value = !isOpen.value }
const close = () => { isOpen.value = false }

const handleLogout = () => {
  close()
  emit('logout') // выход, уведомление и переход выполняет NavBar
}

const handleClickOutside = (e) => {
  if (menuRef.value && !menuRef.value.contains(e.target)) {
    close()
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
@import '@/assets/styles/user-menu.css';
.faculty-note {
  display: block;
  margin-top: 0.15rem;
  color: var(--text-muted);
  font-weight: 400;
}
</style>
