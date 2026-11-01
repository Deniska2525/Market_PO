<template>
  <div class="u-page">
    <div class="u-header">
      <div>
        <h1>Каталог разработок</h1>
        <p class="u-subtitle">Проекты, технологии и разработки вуза по факультетам</p>
      </div>
    </div>

    <form class="u-filters" @submit.prevent="pushQuery">
      <label class="sr-only" for="catalog-q">Поиск по каталогу</label>
      <input id="catalog-q" v-model="filters.q" type="search" placeholder="Поиск по названию, описанию и тегам">
      <label class="sr-only" for="catalog-faculty">Факультет</label>
      <select id="catalog-faculty" v-model="filters.faculty_id" @change="pushQuery">
        <option value="">Все факультеты</option>
        <option v-for="f in faculties" :key="f.id" :value="String(f.id)">{{ f.name }}</option>
      </select>
      <label class="sr-only" for="catalog-readiness">Готовность</label>
      <select id="catalog-readiness" v-model="filters.readiness" @change="pushQuery">
        <option value="">Любая готовность</option>
        <option v-for="(label, value) in READINESS_LABELS" :key="value" :value="value">{{ label }}</option>
      </select>
      <button class="btn btn-secondary" type="submit">Найти</button>
      <button v-if="hasFilters" class="btn btn-secondary" type="button" @click="clear">Сбросить</button>
    </form>

    <div v-if="tags.length" class="u-chips tags" aria-label="Теги">
      <button
        v-for="t in tags"
        :key="t.id"
        type="button"
        class="u-chip tag"
        :class="{ 'u-chip--active': filters.tag === t.name }"
        :aria-pressed="filters.tag === t.name"
        @click="toggleTag(t.name)"
      >{{ t.name }} <small>{{ t.count }}</small></button>
    </div>

    <div v-if="error" class="u-alert">{{ error }}</div>
    <div v-if="loading && !cards.length" class="u-state">Загрузка…</div>
    <div v-else-if="!cards.length && !error" class="u-state">
      Ничего не найдено. Измените фильтры или
      <router-link to="/">опишите задачу на главной</router-link>: нейросеть подберёт разработки по смыслу.
    </div>

    <div v-else class="u-grid">
      <CardTile v-for="card in cards" :key="card.id" :card="card" />
    </div>

    <div v-if="hasMore" class="more">
      <button class="btn btn-secondary" :disabled="loading" @click="load(true)">
        {{ loading ? 'Загрузка…' : 'Показать ещё' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import universityService from '../services/university'
import CardTile from '../components/CardTile.vue'
import { READINESS_LABELS, extractErrors } from '../utils/format'

const PAGE_SIZE = 24
const KEYS = ['q', 'faculty_id', 'tag', 'readiness']

const route = useRoute()
const router = useRouter()

const cards = ref([])
const faculties = ref([])
const tags = ref([])
const loading = ref(true)
const error = ref('')
const hasMore = ref(false)
const filters = reactive({ q: '', faculty_id: '', tag: '', readiness: '' })

const hasFilters = computed(() => KEYS.some(k => filters[k]))

// Единственный источник правды — адрес страницы: фильтры можно сохранить в закладку
// и открыть по ссылке с главной, из списка факультетов или с карточки
function readQuery() {
  for (const key of KEYS) filters[key] = route.query[key] ? String(route.query[key]) : ''
}

function pushQuery() {
  const query = {}
  for (const key of KEYS) if (filters[key]) query[key] = filters[key]
  router.replace({ query })
}

const toggleTag = name => {
  filters.tag = filters.tag === name ? '' : name
  pushQuery()
}

const clear = () => {
  KEYS.forEach(k => { filters[k] = '' })
  pushQuery()
}

async function load(append = false) {
  loading.value = true
  error.value = ''
  try {
    const rows = await universityService.getCards({
      q: filters.q.trim() || undefined,
      faculty_id: filters.faculty_id || undefined,
      tag: filters.tag || undefined,
      readiness: filters.readiness || undefined,
      skip: append ? cards.value.length : 0,
      limit: PAGE_SIZE
    })
    cards.value = append ? [...cards.value, ...rows] : rows
    hasMore.value = rows.length === PAGE_SIZE
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
}

async function loadTags() {
  try {
    tags.value = await universityService.getTags({ faculty_id: filters.faculty_id || undefined, limit: 24 })
  } catch (e) { /* теги — подсказка, без них каталог работает */ }
}

watch(() => route.query, () => {
  readQuery()
  load(false)
  loadTags()
})

onMounted(async () => {
  readQuery()
  try {
    faculties.value = await universityService.getFaculties()
  } catch (e) { /* фильтр по факультетам необязателен */ }
  await Promise.all([load(false), loadTags()])
})
</script>

<style scoped>
.tags { margin-bottom: 1.2rem; }
.tag { border: none; cursor: pointer; }
.tag small { opacity: 0.75; }
.more { text-align: center; margin-top: 1.5rem; }
</style>
