<template>
  <div class="home">
    <section class="hero">
      <div class="hero-inner">
        <h1>Найдите разработку вуза под вашу задачу</h1>
        <p>
          Опишите, что вам нужно, обычными словами. Нейросеть подберёт подходящие разработки, даже если
          называются они иначе: например, для робота найдутся решения по компьютерному зрению.
        </p>

        <form class="search" @submit.prevent="search">
          <label for="ai-query" class="sr-only">Опишите вашу задачу</label>
          <textarea
            id="ai-query"
            v-model="query"
            rows="2"
            maxlength="500"
            placeholder="Например: нужен робот для склада"
            @keydown.enter.exact.prevent="search"
          ></textarea>
          <button class="btn btn-primary" type="submit" :disabled="loading || !query.trim()">
            {{ loading ? 'Подбираем…' : 'Подобрать' }}
          </button>
        </form>

        <div class="examples">
          <span>Попробуйте:</span>
          <button v-for="e in EXAMPLES" :key="e" type="button" class="example" @click="useExample(e)">{{ e }}</button>
        </div>
      </div>
    </section>

    <div class="u-page">
      <section v-if="result" class="results" aria-live="polite">
        <div class="u-header">
          <h2>Результаты подбора</h2>
          <button class="btn btn-secondary" @click="reset">Сбросить</button>
        </div>

        <div class="u-notice">
          <span class="u-badge" :class="result.mode === 'ai' ? 'u-badge--success' : 'u-badge--neutral'">
            {{ result.mode === 'ai' ? 'Подбор нейросетью' : 'Поиск по словам' }}
          </span>
          {{ result.message }}
        </div>

        <div v-if="result.terms.length" class="terms">
          <span class="u-muted">Искали по темам:</span>
          <div class="u-chips">
            <router-link
              v-for="t in result.terms"
              :key="t"
              class="u-chip"
              :to="{ path: '/cards', query: { q: t } }"
            >{{ t }}</router-link>
          </div>
        </div>

        <div v-if="result.results.length" class="u-grid">
          <CardTile v-for="item in result.results" :key="item.card.id" :card="item.card" :reason="item.reason" />
        </div>
        <div v-else class="u-state">
          Подходящих разработок не нашлось. Попробуйте описать задачу иначе или
          <router-link to="/cards">откройте весь каталог</router-link>.
        </div>
      </section>

      <template v-else>
        <section class="block">
          <div class="u-header">
            <h2>Факультеты</h2>
            <router-link to="/faculties" class="btn btn-secondary">Все факультеты</router-link>
          </div>
          <div v-if="!faculties.length" class="u-state">Факультетов пока нет.</div>
          <div v-else class="u-chips faculty-chips">
            <router-link
              v-for="f in faculties"
              :key="f.id"
              class="u-chip faculty-chip"
              :to="{ path: '/cards', query: { faculty_id: f.id } }"
            >{{ f.name }} · {{ f.cards_count }}</router-link>
          </div>
        </section>

        <section class="block">
          <div class="u-header">
            <h2>Свежие разработки</h2>
            <router-link to="/cards" class="btn btn-secondary">Весь каталог</router-link>
          </div>
          <div v-if="!latest.length" class="u-state">Опубликованных разработок пока нет.</div>
          <div v-else class="u-grid">
            <CardTile v-for="card in latest" :key="card.id" :card="card" />
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import universityService from '../services/university'
import CardTile from '../components/CardTile.vue'
import { useNotify } from '../composables/useNotify'
import { extractErrors } from '../utils/format'

const EXAMPLES = [
  'Нужен робот для склада',
  'Как быстро проверить качество воды',
  'Ищем лёгкие материалы для конструкций',
  'Автоматизировать анализ медицинских снимков'
]

const notify = useNotify()
const query = ref('')
const loading = ref(false)
const result = ref(null)
const faculties = ref([])
const latest = ref([])

async function search() {
  const text = query.value.trim()
  if (!text || loading.value) return
  loading.value = true
  try {
    result.value = await universityService.aiSearch(text)
  } catch (e) {
    notify.error(extractErrors(e).message, { title: 'Не удалось выполнить поиск' })
  } finally {
    loading.value = false
  }
}

function useExample(text) {
  query.value = text
  search()
}

function reset() {
  result.value = null
  query.value = ''
}

onMounted(async () => {
  const [f, c] = await Promise.allSettled([
    universityService.getFaculties(),
    universityService.getCards({ limit: 6 })
  ])
  if (f.status === 'fulfilled') faculties.value = f.value
  if (c.status === 'fulfilled') latest.value = c.value
})
</script>

<style scoped>
.hero {
  background: var(--hero-gradient);
  color: #fff;
  padding: 3.5rem 1rem 3rem;
}
.hero-inner { max-width: 820px; margin: 0 auto; text-align: center; }
.hero h1 { font-size: 2.2rem; line-height: 1.2; margin-bottom: 0.8rem; }
.hero p { opacity: 0.95; line-height: 1.55; margin-bottom: 1.6rem; }

.search { display: flex; gap: 0.6rem; align-items: stretch; }
.search textarea {
  flex: 1;
  resize: none;
  padding: 0.8rem 1rem;
  border: 2px solid transparent;
  border-radius: 12px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 1rem;
  font-family: inherit;
}
.search .btn { padding: 0 1.6rem; white-space: nowrap; }

.examples { display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: center; align-items: center; margin-top: 1rem; font-size: 0.9rem; }
.example {
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border-radius: 999px;
  padding: 0.25rem 0.8rem;
  cursor: pointer;
  font-size: 0.85rem;
}
.example:hover { background: rgba(255, 255, 255, 0.25); }

.block { margin-bottom: 2.2rem; }
.terms { margin-bottom: 1.2rem; display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }
.faculty-chips { gap: 0.6rem; }
.faculty-chip { padding: 0.5rem 1rem; font-size: 0.95rem; background: var(--bg-card); border: 1px solid var(--border-color); }

@media (max-width: 640px) {
  .hero h1 { font-size: 1.6rem; }
  .search { flex-direction: column; }
  .search .btn { padding: 0.8rem; }
}
</style>
