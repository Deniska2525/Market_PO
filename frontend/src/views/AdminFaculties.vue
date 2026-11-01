<template>
  <div>
    <div class="u-header">
      <div>
        <h2>Факультеты</h2>
        <p class="u-subtitle">Карточки и администраторы привязываются к факультету</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">➕ Новый факультет</button>
    </div>

    <div v-if="error" class="u-alert">{{ error }}</div>
    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="!faculties.length" class="u-state">Факультетов пока нет. Создайте первый.</div>

    <div v-else class="u-table-wrap">
      <table class="u-table">
        <thead>
          <tr>
            <th>Название</th>
            <th>Сокращение</th>
            <th>Опубликовано</th>
            <th class="u-col-actions">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in faculties" :key="f.id">
            <td>
              <strong>{{ f.name }}</strong>
              <div v-if="f.description" class="u-muted">{{ f.description }}</div>
            </td>
            <td>{{ f.short_name || '—' }}</td>
            <td>{{ f.cards_count }}</td>
            <td class="u-col-actions">
              <button class="u-icon-btn" title="Редактировать" aria-label="Редактировать" @click="openEdit(f)">✏️</button>
              <button class="u-icon-btn" title="Удалить" aria-label="Удалить" @click="askDelete(f)">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @mousedown.self="closeModal">
      <div ref="panel" class="modal-content" role="dialog" aria-modal="true" aria-labelledby="faculty-title" tabindex="-1">
        <h3 id="faculty-title">{{ editing ? 'Редактировать факультет' : 'Новый факультет' }}</h3>
        <form @submit.prevent="save">
          <div class="form-group">
            <label for="faculty-name">Название *</label>
            <input id="faculty-name" v-model="form.name" type="text" maxlength="150" required>
          </div>
          <div class="form-group">
            <label for="faculty-short">Сокращение</label>
            <input id="faculty-short" v-model="form.short_name" type="text" maxlength="20" placeholder="Например: ФК">
          </div>
          <div class="form-group">
            <label for="faculty-desc">Описание</label>
            <textarea id="faculty-desc" v-model="form.description" rows="3" maxlength="2000"></textarea>
          </div>
          <div v-if="modalError" class="u-alert" role="alert">{{ modalError }}</div>
          <div class="u-form-actions">
            <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? 'Сохранение…' : 'Сохранить' }}</button>
            <button type="button" class="btn btn-secondary" :disabled="saving" @click="closeModal">Отмена</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import universityService from '../services/university'
import { useNotify } from '../composables/useNotify'
import { useDialogA11y } from '../composables/useDialogA11y'
import { extractErrors } from '../utils/format'

const notify = useNotify()

const faculties = ref([])
const loading = ref(true)
const error = ref('')
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const modalError = ref('')
const form = reactive({ name: '', short_name: '', description: '' })
const panel = ref(null)

useDialogA11y({ panel, active: computed(() => showModal.value), onEscape: () => { if (!saving.value) showModal.value = false } })

async function load() {
  loading.value = true
  error.value = ''
  try {
    faculties.value = await universityService.getFaculties()
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', short_name: '', description: '' })
  modalError.value = ''
  showModal.value = true
}

function openEdit(faculty) {
  editing.value = faculty
  Object.assign(form, {
    name: faculty.name,
    short_name: faculty.short_name || '',
    description: faculty.description || ''
  })
  modalError.value = ''
  showModal.value = true
}

function closeModal() {
  if (!saving.value) showModal.value = false
}

async function save() {
  modalError.value = ''
  if (form.name.trim().length < 2) {
    modalError.value = 'Название должно быть не короче 2 символов'
    return
  }
  saving.value = true
  const wasEditing = !!editing.value
  const payload = {
    name: form.name.trim(),
    short_name: form.short_name.trim() || null,
    description: form.description.trim() || null
  }
  try {
    if (wasEditing) await universityService.updateFaculty(editing.value.id, payload)
    else await universityService.createFaculty(payload)
    showModal.value = false
    notify.success(wasEditing ? 'Факультет обновлён' : 'Факультет создан')
    await load()
  } catch (e) {
    modalError.value = extractErrors(e).message
  } finally {
    saving.value = false
  }
}

async function askDelete(faculty) {
  const done = await notify.confirm({
    title: 'Удалить факультет?',
    message: `Факультет «${faculty.name}» будет удалён. Если к нему привязаны карточки или администраторы, удаление не получится.`,
    confirmText: 'Удалить',
    danger: true,
    action: () => universityService.deleteFaculty(faculty.id)
  })
  if (!done) return
  notify.success(`Факультет «${faculty.name}» удалён`)
  await load()
}

onMounted(load)
</script>
