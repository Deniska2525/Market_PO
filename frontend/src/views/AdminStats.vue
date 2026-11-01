<template>
  <div>
    <div class="u-header">
      <div>
        <h2>Обзор</h2>
        <p class="u-subtitle">Состояние витрины разработок</p>
      </div>
    </div>

    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="error" class="u-alert">{{ error }}</div>

    <template v-else-if="stats">
      <div class="u-stats">
        <router-link to="/admin/faculties" class="u-stat"><strong>{{ stats.faculties }}</strong><span>Факультетов</span></router-link>
        <router-link to="/manage" class="u-stat"><strong>{{ stats.cards_total }}</strong><span>Карточек всего</span></router-link>
        <div class="u-stat"><strong>{{ stats.cards_published }}</strong><span>Опубликовано</span></div>
        <router-link to="/manage/inquiries" class="u-stat"><strong>{{ stats.inquiries_new }}</strong><span>Новых заявок</span></router-link>
        <router-link to="/admin/users" class="u-stat"><strong>{{ stats.users_total }}</strong><span>Пользователей</span></router-link>
        <router-link to="/admin/users?role=admin" class="u-stat"><strong>{{ stats.admins_total }}</strong><span>Администраторов факультетов</span></router-link>
      </div>

      <div class="u-notice">
        <strong>С чего начать.</strong> Создайте факультет в разделе «Факультеты», затем в разделе «Пользователи»
        заведите для него администратора: он сможет добавлять и редактировать карточки только своего факультета.
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import universityService from '../services/university'
import { extractErrors } from '../utils/format'

const stats = ref(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    stats.value = await universityService.getAdminStats()
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
})
</script>
