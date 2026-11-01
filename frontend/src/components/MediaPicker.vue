<template>
  <div class="media-picker" :class="{ invalid }">
    <div v-if="ids.length" class="items" :class="kind">
      <div v-for="(id, i) in ids" :key="id" class="item">
        <img v-if="kind === 'image'" :src="imageSrc(id)" alt="" loading="lazy">
        <div v-else class="file-chip">📦 {{ labelFor(id) }}</div>
        <div class="item-actions">
          <button v-if="multiple && i > 0" type="button" title="Левее" @click="move(i, -1)">←</button>
          <button v-if="multiple && i < ids.length - 1" type="button" title="Правее" aria-label="Правее" @click="move(i, 1)">→</button>
          <button type="button" title="Убрать из записи" aria-label="Убрать из записи" @click="remove(id)">✕</button>
        </div>
      </div>
    </div>

    <div class="controls">
      <label class="btn btn-secondary upload-btn" :class="{ disabled: busy || full }">
        {{ busy ? `Загрузка… ${progress}%` : '⬆️ Загрузить' }}
        <input
          type="file"
          hidden
          :accept="kind === 'image' ? IMAGE_ACCEPT : FILE_ACCEPT"
          :multiple="multiple"
          :disabled="busy || full"
          @change="onFilesChosen"
        >
      </label>
      <button type="button" class="btn btn-secondary" :disabled="busy" @click="openLibrary">🗂 Из библиотеки</button>
      <small v-if="multiple" class="counter">{{ ids.length }} из {{ maxItems }}</small>
    </div>

    <small v-if="error" class="error">{{ error }}</small>

    <div v-if="showLibrary" class="modal-overlay" @click.self="showLibrary = false">
      <div class="modal-content lib">
        <h3>{{ kind === 'image' ? 'Изображения' : 'Файлы' }} в библиотеке</h3>
        <div v-if="libLoading" class="muted">Загрузка…</div>
        <div v-else-if="!library.length" class="muted">Пока пусто — загрузите файл кнопкой «Загрузить».</div>
        <div v-else class="lib-grid" :class="kind">
          <button
            v-for="m in library"
            :key="m.id"
            type="button"
            class="lib-item"
            :class="{ picked: ids.includes(m.id) }"
            @click="pick(m)"
          >
            <img v-if="m.kind === 'image'" :src="apiUrl(m.url)" alt="" loading="lazy">
            <span class="lib-name">{{ m.filename }}</span>
            <small>{{ formatBytes(m.size) }}</small>
          </button>
        </div>
        <div class="lib-actions">
          <button type="button" class="btn btn-secondary" @click="showLibrary = false">Готово</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import universityService, { apiUrl } from '../services/university'
import { FILE_ACCEPT, IMAGE_ACCEPT, extractErrors, formatBytes } from '../utils/format'
import { useNotify } from '../composables/useNotify'

const props = defineProps({
  modelValue: { default: null }, // число (одиночный выбор) или массив чисел (галерея)
  kind: { type: String, default: 'image' }, // image | file
  multiple: { type: Boolean, default: false },
  maxItems: { type: Number, default: 20 },
  invalid: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const notify = useNotify()
const busy = ref(false)
const progress = ref(0)
const error = ref('')
const showLibrary = ref(false)
const libLoading = ref(false)
const library = ref([])
const known = ref({}) // id -> метаданные файла, чтобы показывать имена

const ids = computed(() => {
  if (props.multiple) return Array.isArray(props.modelValue) ? props.modelValue : []
  return props.modelValue ? [props.modelValue] : []
})
const full = computed(() => props.multiple && ids.value.length >= props.maxItems)

const imageSrc = id => apiUrl(`/media/${id}/file`)
const labelFor = id => known.value[id]?.filename || `Файл #${id}`

function emitIds(next) {
  emit('update:modelValue', props.multiple ? next : (next[0] ?? null))
}

function remember(items) {
  const copy = { ...known.value }
  for (const item of items) copy[item.id] = item
  known.value = copy
}

async function uploadOne(file) {
  const media = await universityService.uploadMedia(file, props.kind, value => { progress.value = value })
  remember([media])
  return media.id
}

async function onFilesChosen(event) {
  const input = event.target
  const files = [...(input.files || [])]
  input.value = '' // чтобы тот же файл можно было выбрать повторно
  if (!files.length) return

  error.value = ''
  busy.value = true
  progress.value = 0
  try {
    let next = [...ids.value]
    let uploaded = 0
    for (const file of props.multiple ? files : files.slice(0, 1)) {
      if (props.multiple && next.length >= props.maxItems) break
      const id = await uploadOne(file)
      next = props.multiple ? [...next, id] : [id]
      uploaded += 1
      emitIds(next) // сразу, чтобы при сбое на следующем файле загруженное не потерялось
    }
    if (uploaded) notify.success(uploaded > 1 ? `Загружено файлов: ${uploaded}` : 'Файл загружен')
  } catch (e) {
    error.value = extractErrors(e).message
    notify.error(error.value, { title: 'Не удалось загрузить файл' })
  } finally {
    busy.value = false
  }
}

async function loadLibrary() {
  libLoading.value = true
  try {
    library.value = await universityService.listMedia({ kind: props.kind, limit: 100 })
    remember(library.value)
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    libLoading.value = false
  }
}

async function openLibrary() {
  error.value = ''
  showLibrary.value = true
  await loadLibrary()
}

function pick(media) {
  if (!props.multiple) {
    emitIds([media.id])
    showLibrary.value = false
    return
  }
  if (ids.value.includes(media.id)) emitIds(ids.value.filter(id => id !== media.id))
  else if (!full.value) emitIds([...ids.value, media.id])
}

function remove(id) {
  emitIds(ids.value.filter(item => item !== id))
}

function move(index, delta) {
  const next = [...ids.value]
  next.splice(index + delta, 0, next.splice(index, 1)[0])
  emitIds(next)
}

// Для файлов нужны имена: подгружаем библиотеку один раз, ошибки здесь не показываем
onMounted(async () => {
  if (props.kind === 'file' && ids.value.length) {
    try {
      remember(await universityService.listMedia({ kind: 'file', limit: 100 }))
    } catch (e) { /* имена не критичны */ }
  }
})
</script>

<style scoped>
.media-picker { border: 1px dashed var(--border-color); border-radius: 10px; padding: 0.8rem; background: var(--bg-secondary); }
.media-picker.invalid { border-color: var(--danger-text); }
.items { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-bottom: 0.7rem; }
.item { position: relative; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-card); overflow: hidden; }
.items.image .item img { display: block; width: 110px; height: 110px; object-fit: cover; }
.file-chip { padding: 0.6rem 0.8rem; color: var(--text-primary); font-size: 0.9rem; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-actions { display: flex; gap: 0.2rem; padding: 0.2rem; justify-content: flex-end; }
.items.image .item-actions { position: absolute; top: 0; right: 0; left: 0; padding: 0.2rem; background: linear-gradient(rgba(0, 0, 0, 0.45), transparent); }
.item-actions button { border: none; background: rgba(0, 0, 0, 0.55); color: #fff; border-radius: 4px; cursor: pointer; padding: 0.1rem 0.4rem; font-size: 0.8rem; }
.items.file .item-actions button { background: var(--bg-tertiary); color: var(--text-secondary); }
.controls { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.upload-btn { cursor: pointer; }
.upload-btn.disabled { opacity: 0.55; cursor: not-allowed; }
.counter { color: var(--text-muted); }
.error { display: block; margin-top: 0.5rem; color: var(--danger-text); }
.muted { color: var(--text-muted); padding: 1rem 0; }

.lib { max-width: 760px; }
.lib-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 0.6rem; margin-bottom: 1rem; }
.lib-grid.file { grid-template-columns: 1fr; }
.lib-item { display: flex; flex-direction: column; gap: 0.2rem; text-align: left; border: 2px solid var(--border-color); border-radius: 8px; background: var(--bg-card); color: var(--text-primary); padding: 0.4rem; cursor: pointer; }
.lib-item:hover { border-color: var(--primary-color); }
.lib-item.picked { border-color: var(--primary-color); background: var(--hover-bg); }
.lib-item img { width: 100%; height: 90px; object-fit: cover; border-radius: 4px; }
.lib-name { font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lib-actions { display: flex; justify-content: flex-end; }
</style>
