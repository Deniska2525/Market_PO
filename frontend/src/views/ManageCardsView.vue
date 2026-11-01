<template>
  <div class="u-page">
    <div class="u-header">
      <div>
        <h1>Карточки разработок</h1>
        <p class="u-subtitle">
          {{ authStore.isSuperuser ? 'Все факультеты' : `Факультет: ${authStore.facultyName}` }}
        </p>
      </div>
      <div class="u-actions">
        <router-link to="/manage/inquiries" class="btn btn-secondary">
          📨 Заявки<span v-if="stats && stats.inquiries_new" class="count">{{ stats.inquiries_new }}</span>
        </router-link>
        <router-link to="/manage/cards/new" class="btn btn-primary">➕ Новая карточка</router-link>
      </div>
    </div>

    <div v-if="stats" class="u-stats">
      <div class="u-stat"><strong>{{ stats.cards_total }}</strong><span>Всего карточек</span></div>
      <div class="u-stat"><strong>{{ stats.cards_published }}</strong><span>Опубликовано</span></div>
      <div class="u-stat"><strong>{{ stats.cards_draft }}</strong><span>Черновики</span></div>
      <router-link to="/manage/inquiries" class="u-stat"><strong>{{ stats.inquiries_new }}</strong><span>Новые заявки</span></router-link>
    </div>

    <form class="u-filters" @submit.prevent="reload">
      <label class="sr-only" for="manage-q">Поиск по названию</label>
      <input id="manage-q" v-model="filters.q" type="search" placeholder="Поиск по названию">
      <label class="sr-only" for="manage-status">Статус</label>
      <select id="manage-status" v-model="filters.status" @change="reload">
        <option value="">Любой статус</option>
        <option v-for="(label, value) in STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
      </select>
      <template v-if="authStore.isSuperuser">
        <label class="sr-only" for="manage-faculty">Факультет</label>
        <select id="manage-faculty" v-model="filters.faculty_id" @change="reload">
          <option value="">Все факультеты</option>
          <option v-for="f in faculties" :key="f.id" :value="String(f.id)">{{ f.name }}</option>
        </select>
      </template>
      <button class="btn btn-secondary" type="submit">Найти</button>
    </form>

    <div v-if="error" class="u-alert">{{ error }}</div>
    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="!cards.length" class="u-state">
      Карточек нет. <router-link to="/manage/cards/new">Создайте первую</router-link>.
    </div>

    <div v-else class="u-table-wrap">
      <table class="u-table">
        <thead>
          <tr>
            <th>Название</th>
            <th v-if="authStore.isSuperuser">Факультет</th>
            <th>Статус</th>
            <th>Изменено</th>
            <th class="u-col-actions">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="card in cards" :key="card.id">
            <td>
              <router-link :to="`/manage/cards/${card.id}`" class="title">{{ card.title }}</router-link>
              <div class="u-muted summary">{{ card.summary }}</div>
            </td>
            <td v-if="authStore.isSuperuser">{{ card.faculty_short_name || card.faculty_name }}</td>
            <td><span class="u-badge" :class="STATUS_BADGES[card.status]">{{ STATUS_LABELS[card.status] || card.status }}</span></td>
            <td>{{ formatDate(card.updated_at) }}</td>
            <td class="u-col-actions">
              <router-link :to="`/manage/cards/${card.id}`" class="u-icon-btn" title="Редактировать" aria-label="Редактировать">✏️</router-link>
              <button
                class="u-icon-btn"
                :title="card.status === 'published' ? 'Скрыть из каталога' : 'Опубликовать'"
                :aria-label="card.status === 'published' ? 'Скрыть из каталога' : 'Опубликовать'"
                @click="toggleStatus(card)"
              >{{ card.status === 'published' ? '🙈' : '🚀' }}</button>
              <router-link :to="`/cards/${card.id}`" class="u-icon-btn" title="Открыть страницу" aria-label="Открыть страницу">↗️</router-link>
              <button class="u-icon-btn" title="Удалить" aria-label="Удалить" @click="askDelete(card)">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="page > 0 || hasNext" class="u-pager">
      <button class="btn btn-secondary" :disabled="page === 0 || loading" @click="goPage(-1)">← Назад</button>
      <span>Страница {{ page + 1 }}</span>
      <button class="btn btn-secondary" :disabled="!hasNext || loading" @click="goPage(1)">Вперёд →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import universityService from '../services/university'
import { useAuthStore } from '../stores/auth'
import { useNotify } from '../composables/useNotify'
import { STATUS_LABELS, STATUS_BADGES, extractErrors, formatDate } from '../utils/format'

const PAGE_SIZE = 20

const authStore = useAuthStore()
const notify = useNotify()

const cards = ref([])
const faculties = ref([])
const stats = ref(null)
const loading = ref(true)
const error = ref('')
const page = ref(0)
const filters = reactive({ q: '', status: '', faculty_id: '' })

const hasNext = computed(() => cards.value.length === PAGE_SIZE)

async function load() {
  loading.value = true
  error.value = ''
  try {
    cards.value = await universityService.manageCards({
      q: filters.q.trim() || undefined,
      status: filters.status || undefined,
      faculty_id: filters.faculty_id || undefined,
      skip: page.value * PAGE_SIZE,
      limit: PAGE_SIZE
    })
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await universityService.manageStats()
  } catch (e) { /* счётчики не критичны */ }
}

function reload() {
  page.value = 0
  load()
}

function goPage(delta) {
  page.value += delta
  load()
}

async function toggleStatus(card) {
  const next = card.status === 'published' ? 'draft' : 'published'
  try {
    await universityService.setCardStatus(card.id, next)
    notify.success(next === 'published' ? `«${card.title}» опубликована` : `«${card.title}» скрыта из каталога`)
    await Promise.all([load(), loadStats()])
  } catch (e) {
    notify.fail(e, 'Не удалось изменить статус')
  }
}

async function askDelete(card) {
  const done = await notify.confirm({
    title: 'Удалить карточку?',
    message: `Карточка «${card.title}» и все заявки по ней будут удалены без возможности восстановления.`,
    confirmText: 'Удалить',
    danger: true,
    action: () => universityService.deleteCard(card.id)
  })
  if (!done) return
  notify.success(`Карточка «${card.title}» удалена`)
  if (cards.value.length === 1 && page.value > 0) page.value -= 1
  await Promise.all([load(), loadStats()])
}

onMounted(async () => {
  if (authStore.isSuperuser) {
    try {
      faculties.value = await universityService.getFaculties()
    } catch (e) { /* фильтр по факультетам необязателен */ }
  }
  await Promise.all([load(), loadStats()])
})
</script>

<style scoped>
.title { color: var(--text-primary); font-weight: 600; text-decoration: none; }
.title:hover { color: var(--primary-color); }
.summary { margin-top: 0.15rem; max-width: 460px; }
.count {
  display: inline-block;
  margin-left: 0.4rem;
  min-width: 1.3rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: var(--danger-text);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  text-align: center;
}
</style>
