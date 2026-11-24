<template>
  <div class="u-page u-page--narrow">
    <div class="u-header">
      <h1>{{ isEdit ? 'Редактирование карточки' : 'Новая карточка' }}</h1>
      <div class="u-actions">
        <router-link v-if="isEdit" :to="`/cards/${cardId}`" class="btn btn-secondary">
          <AppIcon name="external-link" :size="16" />
          Как видят посетители
        </router-link>
        <router-link to="/manage" class="btn btn-secondary">
          <AppIcon name="arrow-left" :size="16" />
          К списку
        </router-link>
      </div>
    </div>

    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="loadError" class="u-alert">{{ loadError }}</div>

    <form v-else class="u-form" @submit.prevent="save">
      <h3>Основное</h3>

      <div class="form-group">
        <label for="card-faculty">Факультет</label>
        <select v-if="authStore.isSuperuser" id="card-faculty" v-model="form.faculty_id">
          <option value="">— выберите факультет —</option>
          <option v-for="f in faculties" :key="f.id" :value="f.id">{{ f.name }}</option>
        </select>
        <input v-else id="card-faculty" type="text" :value="authStore.facultyName" disabled>
        <small v-if="!authStore.isSuperuser" class="u-hint">Администратор работает только с карточками своего факультета.</small>
      </div>

      <div class="form-group">
        <label for="card-title">Название *</label>
        <input id="card-title" v-model="form.title" type="text" maxlength="200" required>
      </div>

      <div class="form-group">
        <label for="card-summary">Краткое описание * <span class="u-muted">({{ form.summary.length }}/300)</span></label>
        <textarea id="card-summary" v-model="form.summary" rows="3" maxlength="300" required
          placeholder="Одно-два предложения: что это и кому полезно. Показывается в списках и участвует в поиске."></textarea>
      </div>

      <div class="form-group">
        <label>Подробное описание</label>
        <RichTextEditor v-model="form.description" />
      </div>

      <h3>Теги и готовность</h3>

      <div class="form-group">
        <label>Теги</label>
        <TagInput v-model="form.tags" :suggestions="tagSuggestions" :max="10" />
        <small class="u-hint">Теги помогают нейросети находить карточку по смыслу: указывайте технологии и области применения.</small>
      </div>

      <div class="form-group">
        <label for="card-readiness">Уровень готовности</label>
        <select id="card-readiness" v-model="form.readiness">
          <option value="">Не указан</option>
          <option v-for="(label, value) in READINESS_LABELS" :key="value" :value="value">{{ label }}</option>
        </select>
      </div>

      <h3>Изображения</h3>

      <div class="form-group">
        <label>Обложка</label>
        <MediaPicker v-model="form.cover_media_id" kind="image" />
      </div>
      <div class="form-group">
        <label>Галерея (до 6 изображений)</label>
        <MediaPicker v-model="form.gallery_media_ids" kind="image" multiple :max-items="6" />
      </div>

      <h3>Контакты для заявок</h3>

      <div class="u-row2">
        <div class="form-group">
          <label for="card-contact-name">Контактное лицо</label>
          <input id="card-contact-name" v-model="form.contact_name" type="text" maxlength="100">
        </div>
        <div class="form-group">
          <label for="card-contact-email">Email</label>
          <input id="card-contact-email" v-model="form.contact_email" type="email">
        </div>
      </div>
      <div class="u-row2">
        <div class="form-group">
          <label for="card-contact-phone">Телефон</label>
          <input id="card-contact-phone" v-model="form.contact_phone" type="tel" maxlength="30">
        </div>
        <div class="form-group">
          <label for="card-website">Сайт проекта</label>
          <input id="card-website" v-model="form.website" type="url" maxlength="500" placeholder="https://">
        </div>
      </div>

      <h3>Публикация</h3>

      <div class="form-group">
        <label for="card-status">Статус</label>
        <select id="card-status" v-model="form.status">
          <option value="draft">Черновик: карточку видят только сотрудники факультета</option>
          <option value="published">Опубликована: карточка видна в каталоге</option>
        </select>
      </div>

      <div v-if="formError" class="u-alert" role="alert">{{ formError }}</div>

      <div class="u-form-actions">
        <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? 'Сохранение…' : 'Сохранить' }}</button>
        <router-link to="/manage" class="btn btn-secondary">Отмена</router-link>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import universityService from '../services/university'
import { useAuthStore } from '../stores/auth'
import { useNotify } from '../composables/useNotify'
import RichTextEditor from '../components/RichTextEditor.vue'
import MediaPicker from '../components/MediaPicker.vue'
import TagInput from '../components/TagInput.vue'
import { READINESS_LABELS, extractErrors } from '../utils/format'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const notify = useNotify()

const cardId = computed(() => (route.params.id ? Number(route.params.id) : null))
const isEdit = computed(() => cardId.value !== null)

const loading = ref(true)
const saving = ref(false)
const loadError = ref('')
const formError = ref('')
const faculties = ref([])
const tagSuggestions = ref([])

const form = reactive({
  faculty_id: '',
  title: '',
  summary: '',
  description: '',
  tags: [],
  readiness: '',
  cover_media_id: null,
  gallery_media_ids: [],
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  website: '',
  status: 'draft'
})

// --- Несохранённые изменения ---
const snapshot = ref(null)
const serialize = () => JSON.stringify(form)
const dirty = computed(() => snapshot.value !== null && serialize() !== snapshot.value)

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  return notify.confirm({
    title: 'Выйти без сохранения?',
    message: 'Внесённые изменения будут потеряны.',
    confirmText: 'Выйти',
    cancelText: 'Остаться',
    danger: true,
    irreversible: false
  })
})

// Закрытие вкладки и перезагрузка: браузер покажет собственное предупреждение
function onBeforeUnload(event) {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}
window.addEventListener('beforeunload', onBeforeUnload)
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))

function buildPayload() {
  const payload = {
    title: form.title.trim(),
    summary: form.summary.trim(),
    description: form.description || null,
    status: form.status,
    readiness: form.readiness || null,
    cover_media_id: form.cover_media_id || null,
    gallery_media_ids: form.gallery_media_ids,
    tags: form.tags,
    contact_name: form.contact_name.trim() || null,
    contact_email: form.contact_email.trim() || null,
    contact_phone: form.contact_phone.trim() || null,
    website: form.website.trim() || null
  }
  // Администратор факультета всегда работает со своим факультетом — сервер подставит его сам
  if (authStore.isSuperuser) payload.faculty_id = form.faculty_id || null
  return payload
}

async function save() {
  formError.value = ''
  if (authStore.isSuperuser && !form.faculty_id) {
    formError.value = 'Выберите факультет'
    return
  }
  if (!form.title.trim() || !form.summary.trim()) {
    formError.value = 'Заполните название и краткое описание'
    return
  }

  saving.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) await universityService.updateCard(cardId.value, payload)
    else await universityService.createCard(payload)
    snapshot.value = serialize() // сохранено — предупреждать об уходе со страницы не нужно
    notify.success(isEdit.value ? 'Карточка сохранена' : 'Карточка создана')
    router.push('/manage')
  } catch (e) {
    formError.value = extractErrors(e).message
    notify.error(formError.value) // форма длинная: плашка внизу может быть вне экрана
  } finally {
    saving.value = false
  }
}

function fill(card) {
  form.faculty_id = card.faculty_id
  form.title = card.title
  form.summary = card.summary
  form.description = card.description || ''
  form.tags = [...card.tags]
  form.readiness = card.readiness || ''
  form.cover_media_id = card.cover_media_id || null
  form.gallery_media_ids = [...card.gallery_media_ids]
  form.contact_name = card.contact_name || ''
  form.contact_email = card.contact_email || ''
  form.contact_phone = card.contact_phone || ''
  form.website = card.website || ''
  form.status = card.status
}

onMounted(async () => {
  try {
    const [facultyList, tags] = await Promise.all([
      authStore.isSuperuser ? universityService.getFaculties() : Promise.resolve([]),
      universityService.getTags({ limit: 60 }).catch(() => [])
    ])
    faculties.value = facultyList
    tagSuggestions.value = tags.map(t => t.name)
    if (isEdit.value) fill(await universityService.getCard(cardId.value))
    snapshot.value = serialize()
  } catch (e) {
    loadError.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
})
</script>
