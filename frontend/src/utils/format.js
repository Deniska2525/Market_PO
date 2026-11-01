// Общие функции и справочники подписей (без Vue) — проверяются через `node --test`,
// см. format.test.mjs.

export const STATUS_LABELS = { draft: 'Черновик', published: 'Опубликована' }
export const STATUS_BADGES = { draft: 'u-badge--warning', published: 'u-badge--success' }

export const READINESS_LABELS = {
  idea: 'Идея',
  prototype: 'Прототип',
  pilot: 'Пилот',
  ready: 'Готово к внедрению'
}

export const INQUIRY_STATUS_LABELS = { new: 'Новая', in_progress: 'В работе', done: 'Обработана' }
export const INQUIRY_STATUS_BADGES = {
  new: 'u-badge--info',
  in_progress: 'u-badge--warning',
  done: 'u-badge--success'
}

export const ROLE_LABELS = {
  user: 'Пользователь',
  admin: 'Администратор факультета',
  superuser: 'Суперадмин'
}

export const IMAGE_ACCEPT = 'image/png,image/jpeg,image/gif,image/webp'
export const FILE_ACCEPT = '.zip,.7z,.gz,.tgz,.xz,.bz2,.tar,.pdf'

// Разбор ошибки axios: наш 422 приходит строкой в detail, стандартный pydantic — массивом
// объектов {msg}, прочие — строкой; при обрыве связи ответа нет
export function extractErrors(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return { message: detail }
  if (Array.isArray(detail)) {
    return { message: detail.map(d => d.msg).filter(Boolean).join('; ') || 'Некорректные данные' }
  }
  if (error?.response?.status === 429) {
    return { message: 'Слишком много запросов. Подождите немного и попробуйте снова.' }
  }
  if (error?.response) return { message: `Ошибка сервера (${error.response.status})` }
  return { message: 'Нет связи с сервером' }
}

// Сервер отдаёт время в UTC без суффикса «Z» — без него браузер сочтёт его локальным
export function formatDate(iso) {
  if (!iso) return '—'
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso)
  const d = new Date(hasZone ? iso : `${iso}Z`)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })
}

export function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(Number(bytes))) return '—'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  let value = Number(bytes)
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  return `${value >= 10 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`
}

// pluralRu(5, ['карточка', 'карточки', 'карточек']) -> 'карточек'
export function pluralRu(n, forms) {
  const abs = Math.abs(n) % 100
  const last = abs % 10
  if (abs > 10 && abs < 20) return forms[2]
  if (last > 1 && last < 5) return forms[1]
  if (last === 1) return forms[0]
  return forms[2]
}

// Тег в том виде, в каком его хранит сервер: «  Компьютерное   Зрение » -> «компьютерное зрение»
export function normalizeTagInput(text) {
  return String(text ?? '').replace(/\s+/g, ' ').trim().toLowerCase().replace(/ё/g, 'е')
}

// Обложка и картинки лежат на сервере; для <img> нужен абсолютный адрес — см. apiUrl() в services/university.js
export function initials(name) {
  const words = String(name || '').trim().split(/\s+/).filter(Boolean)
  return (words.slice(0, 2).map(w => w[0]).join('') || '?').toUpperCase()
}
