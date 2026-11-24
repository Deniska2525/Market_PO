<template>
  <div>
    <div class="u-header">
      <div>
        <h2>Теги</h2>
        <p class="u-subtitle">Теги опубликованных карточек. Удаление снимает тег со всех карточек.</p>
      </div>
    </div>

    <div v-if="error" class="u-alert">{{ error }}</div>
    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="!tags.length" class="u-state">Тегов пока нет.</div>

    <div v-else class="u-table-wrap">
      <table class="u-table">
        <thead>
          <tr>
            <th>Тег</th>
            <th>Карточек</th>
            <th class="u-col-actions">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tags" :key="t.id">
            <td><router-link :to="{ path: '/cards', query: { tag: t.name } }">{{ t.name }}</router-link></td>
            <td>{{ t.count }}</td>
            <td class="u-col-actions">
              <button class="u-icon-btn" title="Удалить" aria-label="Удалить" @click="askDelete(t)"><AppIcon name="trash" :size="18" /></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import universityService from '../services/university'
import { useNotify } from '../composables/useNotify'
import { extractErrors } from '../utils/format'

const notify = useNotify()
const tags = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    tags.value = await universityService.getTags({ limit: 500 })
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
}

async function askDelete(tag) {
  const done = await notify.confirm({
    title: 'Удалить тег?',
    message: `Тег «${tag.name}» будет снят с ${tag.count} карточек и удалён.`,
    confirmText: 'Удалить',
    danger: true,
    action: () => universityService.deleteTag(tag.id)
  })
  if (!done) return
  notify.success(`Тег «${tag.name}» удалён`)
  await load()
}

onMounted(load)
</script>
