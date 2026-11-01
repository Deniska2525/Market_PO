<template>
  <div>
    <div class="tag-input" :class="{ focused, invalid }" @click="focusInput">
      <span v-for="tag in modelValue" :key="tag" class="tag">
        {{ tag }}
        <button type="button" :aria-label="`Убрать тег ${tag}`" @click.stop="remove(tag)">×</button>
      </span>
      <input
        ref="input"
        v-model="draft"
        type="text"
        :placeholder="modelValue.length ? '' : placeholder"
        :disabled="modelValue.length >= max"
        aria-label="Новый тег"
        @input="onInput"
        @keydown="onKeydown"
        @focus="focused = true"
        @blur="onBlur"
      >
    </div>

    <div v-if="available.length" class="suggestions">
      <span class="u-hint">Уже используются:</span>
      <button v-for="s in available" :key="s" type="button" class="u-chip" @click="add(s)">{{ s }}</button>
    </div>

    <small v-if="error" class="u-error">{{ error }}</small>
    <small v-else class="u-hint">{{ modelValue.length }} из {{ max }}. Enter или запятая добавляют тег.</small>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { normalizeTagInput } from '../utils/format'

const MAX_TAG_LENGTH = 40

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  suggestions: { type: Array, default: () => [] },
  max: { type: Number, default: 10 },
  placeholder: { type: String, default: 'Например: компьютерное зрение' },
  invalid: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const input = ref(null)
const draft = ref('')
const focused = ref(false)
const error = ref('')

const focusInput = () => input.value?.focus()

const available = computed(() => {
  const typed = normalizeTagInput(draft.value)
  return props.suggestions
    .filter(s => !props.modelValue.includes(s) && (!typed || s.includes(typed)))
    .slice(0, 8)
})

function add(text) {
  const tag = normalizeTagInput(text)
  if (!tag) return
  if (tag.length > MAX_TAG_LENGTH) {
    error.value = `Тег длиннее ${MAX_TAG_LENGTH} символов`
    return
  }
  error.value = ''
  if (props.modelValue.includes(tag) || props.modelValue.length >= props.max) return
  emit('update:modelValue', [...props.modelValue, tag])
}

function remove(tag) {
  emit('update:modelValue', props.modelValue.filter(t => t !== tag))
}

function commit() {
  if (draft.value.trim()) add(draft.value)
  draft.value = ''
}

// Вставка «а, б, в» разбивается на отдельные теги
function onInput() {
  if (!draft.value.includes(',')) return
  const parts = draft.value.split(',')
  draft.value = parts.pop()
  parts.forEach(add)
}

function onKeydown(event) {
  if (event.key === 'Enter') {
    event.preventDefault() // Enter в поле тега не должен отправлять форму
    commit()
  } else if (event.key === 'Backspace' && !draft.value && props.modelValue.length) {
    remove(props.modelValue[props.modelValue.length - 1])
  }
}

function onBlur() {
  focused.value = false
  commit()
}
</script>

<style scoped>
.tag-input {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
  padding: 0.4rem 0.5rem;
  border: 1px solid var(--input-border);
  border-radius: 10px;
  background: var(--input-bg);
  cursor: text;
}
.tag-input.focused { border-color: var(--input-focus); }
.tag-input.invalid { border-color: var(--danger-text); }
.tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: var(--hover-bg);
  color: var(--text-primary);
  border-radius: 999px;
  padding: 0.15rem 0.3rem 0.15rem 0.7rem;
  font-size: 0.85rem;
}
.tag button {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.1rem;
  line-height: 1;
  padding: 0 0.3rem;
  border-radius: 50%;
}
.tag button:hover { color: var(--danger-text); }
.tag-input input {
  flex: 1;
  min-width: 140px;
  border: none !important;
  outline: none;
  background: transparent !important;
  color: var(--text-primary);
  padding: 0.3rem;
  box-shadow: none !important;
}
.suggestions { display: flex; gap: 0.35rem; flex-wrap: wrap; align-items: center; margin-top: 0.5rem; }
.suggestions button { border: none; cursor: pointer; }
</style>
