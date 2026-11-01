<template>
  <nav class="navbar" aria-label="Основная навигация">
    <div class="nav-container">
      <router-link to="/" class="logo">Витрина разработок вуза</router-link>

      <div class="nav-links">
        <router-link to="/" class="nav-link" exact-active-class="router-link-active">Главная</router-link>
        <router-link to="/cards" class="nav-link">Каталог</router-link>
        <router-link to="/faculties" class="nav-link">Факультеты</router-link>

        <router-link v-if="authStore.isStaff" to="/manage" class="nav-link staff-link">
          Управление
        </router-link>
        <router-link v-if="authStore.isSuperuser" to="/admin" class="nav-link admin-link">
          Администрирование
        </router-link>

        <ThemeToggle />

        <template v-if="authStore.isAuthenticated">
          <UserMenu :user="authStore.user" @logout="logout" />
        </template>

        <template v-else>
          <router-link to="/login" class="nav-link">Вход</router-link>
          <router-link to="/register" class="nav-link register-btn">Регистрация</router-link>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { useNotify } from '../composables/useNotify'
import UserMenu from './UserMenu.vue'
import ThemeToggle from './ThemeToggle.vue'

const authStore = useAuthStore()
const router = useRouter()
const notify = useNotify()

const logout = async () => {
  await authStore.logout()
  notify.info('Вы вышли из аккаунта')
  router.push('/')
}
</script>

<style scoped>
.navbar {
  background: var(--navbar-bg);
  padding: 1rem 0;
  box-shadow: var(--navbar-shadow);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: all 0.3s;
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--primary-color);
  transition: color 0.3s;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-link {
  color: var(--text-secondary);
  font-weight: 500;
  transition: color 0.2s;
}

.nav-link:hover {
  color: var(--primary-color);
}

.admin-link {
  color: var(--warning-text);
}

.staff-link {
  color: var(--primary-color);
}

.admin-link:hover {
  color: #e67e22;
}

.register-btn {
  background: var(--primary-color);
  color: var(--on-primary);
  padding: 0.5rem 1rem;
  border-radius: 8px;
}

.register-btn:hover {
  background: var(--primary-hover);
  color: var(--on-primary);
}

@media (max-width: 768px) {
  .nav-container {
    flex-direction: column;
    gap: 1rem;
  }
  
  .nav-links {
    flex-wrap: wrap;
    justify-content: center;
    gap: 1rem;
  }
}
</style>
