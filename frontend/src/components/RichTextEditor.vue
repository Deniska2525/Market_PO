<template>
  <div class="rte" :class="{ invalid }">
    <div class="rte-toolbar">
      <button
        v-for="b in buttons"
        :key="b.title"
        type="button"
        :title="b.title"
        @mousedown.prevent="b.run"
      >{{ b.label }}</button>
    </div>
    <div
      ref="editor"
      class="rte-area"
      contenteditable="true"
      @input="emitValue"
      @blur="emitValue"
      @paste="onPaste"
    ></div>
  </div>
</template>

<script setup>
// Лёгкий редактор без зависимостей (contenteditable + execCommand).
// Сервер всё равно пропускает HTML через белый список (backend/app/sanitize.py),
// поэтому здесь важны только удобство и аккуратные ссылки. Позже его можно
// заменить на TipTap: интерфейс (v-model со строкой HTML) останется тем же.
import { ref, onMounted, watch } from 'vue'
import { useNotify } from '../composables/useNotify'

const props = defineProps({
  modelValue: { type: String, default: '' },
  invalid: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const notify = useNotify()
const editor = ref(null)
let lastEmitted = null

function emitValue() {
  const el = editor.value
  if (!el) return
  const isEmpty = el.textContent.trim() === '' && !el.querySelector('img')
  const html = isEmpty ? '' : el.innerHTML
  if (html !== lastEmitted) {
    lastEmitted = html
    emit('update:modelValue', html)
  }
}

function exec(command, value = null) {
  editor.value?.focus()
  document.execCommand(command, false, value)
  emitValue()
}

const LINK_RE = /^(https?:\/\/|mailto:|\/(?!\/))/i

// Диалог забирает фокус у редактора, поэтому выделение запоминаем и возвращаем
async function addLink() {
  const selection = window.getSelection()
  const range = selection && selection.rangeCount ? selection.getRangeAt(0).cloneRange() : null
  const inside = range && editor.value && editor.value.contains(range.commonAncestorContainer)
  if (!inside || range.collapsed) {
    notify.info('Сначала выделите текст, который должен стать ссылкой')
    return
  }

  const url = await notify.prompt({
    title: 'Вставить ссылку',
    message: 'Выделенный текст станет ссылкой.',
    inputLabel: 'Адрес',
    inputPlaceholder: 'https://… или /путь',
    confirmText: 'Вставить',
    validate: value => {
      if (!value) return 'Введите адрес ссылки'
      return LINK_RE.test(value) ? '' : 'Допустимы только ссылки вида https://…, mailto:… или /путь'
    }
  })
  if (!url) return

  editor.value.focus()
  const restored = window.getSelection()
  restored.removeAllRanges()
  restored.addRange(range)
  exec('createLink', url)
}

const buttons = [
  { label: 'B', title: 'Жирный', run: () => exec('bold') },
  { label: 'I', title: 'Курсив', run: () => exec('italic') },
  { label: 'H2', title: 'Заголовок 2', run: () => exec('formatBlock', '<h2>') },
  { label: 'H3', title: 'Заголовок 3', run: () => exec('formatBlock', '<h3>') },
  { label: '¶', title: 'Обычный абзац', run: () => exec('formatBlock', '<p>') },
  { label: '• Список', title: 'Маркированный список', run: () => exec('insertUnorderedList') },
  { label: '1. Список', title: 'Нумерованный список', run: () => exec('insertOrderedList') },
  { label: '❝', title: 'Цитата', run: () => exec('formatBlock', '<blockquote>') },
  { label: '🔗', title: 'Ссылка', run: addLink },
  { label: 'Tx', title: 'Убрать форматирование', run: () => exec('removeFormat') }
]

// Вставляем только текст: чужая разметка из буфера не нужна
function onPaste(event) {
  event.preventDefault()
  const text = event.clipboardData?.getData('text/plain') ?? ''
  document.execCommand('insertText', false, text)
}

function setHtml(html) {
  if (editor.value && editor.value.innerHTML !== html) {
    editor.value.innerHTML = html
  }
}

onMounted(() => {
  lastEmitted = props.modelValue
  setHtml(props.modelValue || '')
})

// Внешнее изменение (загрузили запись, сменили тип); собственные правки сюда не попадают
watch(() => props.modelValue, value => {
  if (value !== lastEmitted) {
    lastEmitted = value
    setHtml(value || '')
  }
})
</script>

<style scoped>
.rte {
  border: 1px solid var(--input-border);
  border-radius: 10px;
  background: var(--input-bg);
  overflow: hidden;
}
.rte:focus-within { border-color: var(--input-focus); }
.rte.invalid { border-color: var(--danger-text); }

.rte-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0.4rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}
.rte-toolbar button {
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
}
.rte-toolbar button:hover {
  background: var(--hover-bg);
  border-color: var(--border-color);
  color: var(--primary-color);
}

.rte-area {
  min-height: 220px;
  max-height: 60vh;
  overflow-y: auto;
  padding: 0.8rem 1rem;
  color: var(--text-primary);
  outline: none;
  line-height: 1.6;
}
.rte-area :deep(h2) { font-size: 1.4rem; margin: 0.8rem 0 0.4rem; }
.rte-area :deep(h3) { font-size: 1.15rem; margin: 0.7rem 0 0.3rem; }
.rte-area :deep(p) { margin: 0.4rem 0; }
.rte-area :deep(ul), .rte-area :deep(ol) { margin: 0.4rem 0; padding-left: 1.5rem; }
.rte-area :deep(blockquote) {
  margin: 0.6rem 0;
  padding-left: 1rem;
  border-left: 3px solid var(--primary-color);
  color: var(--text-secondary);
}
.rte-area :deep(a) { color: var(--primary-color); text-decoration: underline; }
.rte-area :deep(img) { max-width: 100%; }
</style>
