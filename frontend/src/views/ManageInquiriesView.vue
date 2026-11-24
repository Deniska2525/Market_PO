<template>
  <div class="u-page u-page--narrow">
    <div class="u-header">
      <div>
        <h1>Заявки</h1>
        <p class="u-subtitle">
          {{ authStore.isSuperuser ? 'По всем факультетам' : `Факультет: ${authStore.facultyName}` }}
        </p>
      </div>
      <router-link to="/manage" class="btn btn-secondary">
        <AppIcon name="arrow-left" :size="16" />
        К карточкам
      </router-link>
    </div>

    <div class="tabs" role="tablist" aria-label="Статус заявок">
      <button
        v-for="tab in TABS"
        :key="tab.value"
        class="tab"
        :class="{ active: status === tab.value }"
        role="tab"
        :aria-selected="status === tab.value"
        @click="setStatus(tab.value)"
      >{{ tab.label }}</button>
    </div>

    <div v-if="error" class="u-alert">{{ error }}</div>
    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="!items.length" class="u-state">Заявок нет.</div>

    <article v-for="item in items" v-else :key="item.id" class="inquiry u-surface">
      <header>
        <router-link :to="`/cards/${item.card_id}`" class="card-link">{{ item.card_title }}</router-link>
        <span class="u-muted">{{ formatDate(item.created_at) }}</span>
      </header>

      <div class="who">
        <strong>{{ item.name }}</strong>
        <a :href="`mailto:${item.email}`">{{ item.email }}</a>
        <a v-if="item.phone" :href="`tel:${item.phone}`">{{ item.phone }}</a>
        <span v-if="item.organization" class="u-chip">{{ item.organization }}</span>
      </div>

      <p class="message">{{ item.message }}</p>

      <footer>
        <label class="status">
          <span class="sr-only">Статус заявки</span>
          <select :value="item.status" @change="changeStatus(item, $event.target.value)">
            <option v-for="(label, value) in INQUIRY_STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <span class="u-badge" :class="INQUIRY_STATUS_BADGES[item.status]">{{ INQUIRY_STATUS_LABELS[item.status] }}</span>
        <button class="btn btn-secondary small" @click="askDelete(item)">Удалить</button>
      </footer>
    </article>

    <div v-if="page > 0 || hasNext" class="u-pager">
      <button class="btn btn-secondary" :disabled="page === 0 || loading" @click="goPage(-1)">
        <AppIcon name="arrow-left" :size="16" />
        Назад
      </button>
      <span>Страница {{ page + 1 }}</span>
      <button class="btn btn-secondary" :disabled="!hasNext || loading" @click="goPage(1)">
        Вперёд
        <AppIcon name="arrow-right" :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import universityService from '../services/university'
import { useAuthStore } from '../stores/auth'
import { useNotify } from '../composables/useNotify'
import {
  INQUIRY_STATUS_LABELS, INQUIRY_STATUS_BADGES, extractErrors, formatDate
} from '../utils/format'

const PAGE_SIZE = 20
const TABS = [
  { value: '', label: 'Все' },
  { value: 'new', label: 'Новые' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'done', label: 'Обработанные' }
]

const authStore = useAuthStore()
const notify = useNotify()

const items = ref([])
const loading = ref(true)
const error = ref('')
const status = ref('')
const page = ref(0)

const hasNext = computed(() => items.value.length === PAGE_SIZE)

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await universityService.getInquiries({
      status: status.value || undefined,
      skip: page.value * PAGE_SIZE,
      limit: PAGE_SIZE
    })
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
}

function setStatus(value) {
  status.value = value
  page.value = 0
  load()
}

function goPage(delta) {
  page.value += delta
  load()
}

async function changeStatus(item, value) {
  const previous = item.status
  try {
    const updated = await universityService.setInquiryStatus(item.id, value)
    item.status = updated.status
    notify.success(`Статус заявки: ${INQUIRY_STATUS_LABELS[value].toLowerCase()}`)
    if (status.value && status.value !== value) await load() // заявка ушла из текущей вкладки
  } catch (e) {
    item.status = previous
    notify.fail(e, 'Не удалось изменить статус')
    await load()
  }
}

async function askDelete(item) {
  const done = await notify.confirm({
    title: 'Удалить заявку?',
    message: `Заявка от ${item.name} (${item.email}) будет удалена без возможности восстановления.`,
    confirmText: 'Удалить',
    danger: true,
    action: () => universityService.deleteInquiry(item.id)
  })
  if (!done) return
  notify.success('Заявка удалена')
  if (items.value.length === 1 && page.value > 0) page.value -= 1
  await load()
}

onMounted(load)
</script>

<style scoped>
.tabs { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 1.2rem; }
.tab {
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  padding: 0.45rem 1rem;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 500;
}
.tab:hover { border-color: var(--primary-color); color: var(--primary-color); }
.tab.active { background: var(--primary-color); border-color: var(--primary-color); color: var(--on-primary); }

.inquiry { padding: 1rem 1.2rem; margin-bottom: 0.8rem; }
header, footer { display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap; }
header { justify-content: space-between; margin-bottom: 0.6rem; }
.card-link { color: var(--primary-color); font-weight: 600; text-decoration: none; }
.who { display: flex; gap: 0.9rem; flex-wrap: wrap; align-items: center; color: var(--text-primary); margin-bottom: 0.6rem; }
.who a { color: var(--primary-color); }
.message { white-space: pre-wrap; word-break: break-word; color: var(--text-primary); line-height: 1.55; margin-bottom: 0.8rem; }
.status select {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--input-border);
  border-radius: 8px;
  background: var(--input-bg);
  color: var(--text-primary);
}
footer .small { margin-left: auto; padding: 0.35rem 0.9rem; font-size: 0.85rem; }
</style>
