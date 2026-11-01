<template>
  <div class="u-page">
    <div class="u-header">
      <div>
        <h1>Факультеты</h1>
        <p class="u-subtitle">Выберите факультет, чтобы увидеть его разработки</p>
      </div>
    </div>

    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="error" class="u-alert">{{ error }}</div>
    <div v-else-if="!faculties.length" class="u-state">Факультетов пока нет.</div>

    <div v-else class="u-grid">
      <router-link
        v-for="f in faculties"
        :key="f.id"
        :to="{ path: '/cards', query: { faculty_id: f.id } }"
        class="faculty u-surface"
      >
        <div class="top">
          <span class="short">{{ f.short_name || initials(f.name) }}</span>
          <span class="u-badge u-badge--neutral">
            {{ f.cards_count }} {{ pluralRu(f.cards_count, ['разработка', 'разработки', 'разработок']) }}
          </span>
        </div>
        <h3>{{ f.name }}</h3>
        <p v-if="f.description">{{ f.description }}</p>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import universityService from '../services/university'
import { extractErrors, initials, pluralRu } from '../utils/format'

const faculties = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    faculties.value = await universityService.getFaculties()
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.faculty {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.2rem;
  text-decoration: none;
  transition: transform 0.15s, border-color 0.15s;
}
.faculty:hover { transform: translateY(-2px); border-color: var(--primary-color); }
.top { display: flex; justify-content: space-between; align-items: center; }
.short {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 3rem;
  height: 3rem;
  padding: 0 0.6rem;
  border-radius: 12px;
  background: var(--hero-gradient);
  color: var(--on-primary);
  font-weight: 700;
}
h3 { color: var(--text-primary); font-size: 1.1rem; }
p { color: var(--text-secondary); font-size: 0.92rem; line-height: 1.5; }
</style>
