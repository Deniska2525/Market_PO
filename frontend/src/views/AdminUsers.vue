<template>
  <div>
    <div class="u-header">
      <div>
        <h2>Пользователи</h2>
        <p class="u-subtitle">Администраторов факультетов создаёт и назначает суперадмин</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        Администратор факультета
      </button>
    </div>

    <form class="u-filters" @submit.prevent="load">
      <label class="sr-only" for="users-search">Поиск</label>
      <input id="users-search" v-model="filters.search" type="search" placeholder="Логин, имя или email">
      <label class="sr-only" for="users-role">Роль</label>
      <select id="users-role" v-model="filters.role" @change="load">
        <option value="">Все роли</option>
        <option v-for="(label, value) in ROLE_LABELS" :key="value" :value="value">{{ label }}</option>
      </select>
      <label class="sr-only" for="users-faculty">Факультет</label>
      <select id="users-faculty" v-model="filters.faculty_id" @change="load">
        <option value="">Все факультеты</option>
        <option v-for="f in faculties" :key="f.id" :value="String(f.id)">{{ f.name }}</option>
      </select>
      <button class="btn btn-secondary" type="submit">Найти</button>
    </form>

    <div v-if="error" class="u-alert">{{ error }}</div>
    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="!users.length" class="u-state">Пользователей не найдено.</div>

    <div v-else class="u-table-wrap">
      <table class="u-table">
        <thead>
          <tr>
            <th>Пользователь</th>
            <th>Email</th>
            <th>Роль</th>
            <th>Факультет</th>
            <th>Статус</th>
            <th class="u-col-actions">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>
              <strong>{{ u.username }}</strong>
              <div v-if="u.full_name" class="u-muted">{{ u.full_name }}</div>
            </td>
            <td>{{ u.email }}</td>
            <td>
              <span class="u-badge" :class="u.role === 'superuser' ? 'u-badge--warning' : (u.role === 'admin' ? 'u-badge--info' : 'u-badge--neutral')">
                {{ ROLE_LABELS[u.role] || u.role }}
              </span>
            </td>
            <td>
              <template v-if="u.faculty_name">{{ u.faculty_name }}</template>
              <span v-else-if="u.role === 'admin'" class="u-error">не назначен</span>
              <template v-else>—</template>
            </td>
            <td>
              <span class="u-badge" :class="u.is_active ? 'u-badge--success' : 'u-badge--neutral'">
                {{ u.is_active ? 'Активен' : 'Отключён' }}
              </span>
            </td>
            <td class="u-col-actions">
              <template v-if="u.role !== 'superuser'">
                <button class="u-icon-btn" title="Редактировать" aria-label="Редактировать" @click="openEdit(u)"><AppIcon name="edit" :size="18" /></button>
                <button class="u-icon-btn" title="Удалить" aria-label="Удалить" @click="askDelete(u)"><AppIcon name="trash" :size="18" /></button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @mousedown.self="closeModal">
      <div ref="panel" class="modal-content" role="dialog" aria-modal="true" aria-labelledby="user-title" tabindex="-1">
        <h3 id="user-title">{{ editing ? `Пользователь ${editing.username}` : 'Новый администратор факультета' }}</h3>

        <form @submit.prevent="save">
          <template v-if="!editing">
            <div class="form-group">
              <label for="user-username">Логин *</label>
              <input id="user-username" v-model="form.username" type="text" minlength="3" maxlength="50" required autocomplete="off">
            </div>
          </template>

          <div class="form-group">
            <label for="user-fullname">Имя</label>
            <input id="user-fullname" v-model="form.full_name" type="text" maxlength="150">
          </div>
          <div class="form-group">
            <label for="user-email">Email *</label>
            <input id="user-email" v-model="form.email" type="email" required autocomplete="off">
          </div>

          <div v-if="editing" class="form-group">
            <label for="user-role">Роль</label>
            <select id="user-role" v-model="form.role">
              <option value="user">{{ ROLE_LABELS.user }}</option>
              <option value="admin">{{ ROLE_LABELS.admin }}</option>
            </select>
          </div>

          <div v-if="!editing || form.role === 'admin'" class="form-group">
            <label for="user-faculty">Факультет *</label>
            <select id="user-faculty" v-model="form.faculty_id" required>
              <option value="">— выберите факультет —</option>
              <option v-for="f in faculties" :key="f.id" :value="f.id">{{ f.name }}</option>
            </select>
            <small class="u-hint">Администратор видит и редактирует карточки только этого факультета.</small>
          </div>

          <div class="form-group">
            <label for="user-password">{{ editing ? 'Новый пароль (если нужно сменить)' : 'Пароль *' }}</label>
            <input id="user-password" v-model="form.password" type="password" minlength="8" maxlength="72"
              :required="!editing" autocomplete="new-password">
            <small class="u-hint">Не короче 8 символов, с буквами и цифрами.</small>
          </div>

          <label v-if="editing" class="u-check">
            <input v-model="form.is_active" type="checkbox">
            <span>Аккаунт активен (отключённый не может войти)</span>
          </label>

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
import AppIcon from '../components/AppIcon.vue'
import { useRoute } from 'vue-router'
import universityService from '../services/university'
import { useNotify } from '../composables/useNotify'
import { useDialogA11y } from '../composables/useDialogA11y'
import { ROLE_LABELS, extractErrors } from '../utils/format'

const route = useRoute()
const notify = useNotify()

const users = ref([])
const faculties = ref([])
const loading = ref(true)
const error = ref('')
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const modalError = ref('')
const panel = ref(null)

const filters = reactive({ search: '', role: route.query.role ? String(route.query.role) : '', faculty_id: '' })
const form = reactive({
  username: '', full_name: '', email: '', password: '', role: 'admin', faculty_id: '', is_active: true
})

useDialogA11y({ panel, active: computed(() => showModal.value), onEscape: () => { if (!saving.value) showModal.value = false } })

async function load() {
  loading.value = true
  error.value = ''
  try {
    users.value = await universityService.getUsers({
      search: filters.search.trim() || undefined,
      role: filters.role || undefined,
      faculty_id: filters.faculty_id || undefined,
      limit: 100
    })
  } catch (e) {
    error.value = extractErrors(e).message
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { username: '', full_name: '', email: '', password: '', role: 'admin', faculty_id: '', is_active: true })
  modalError.value = ''
  showModal.value = true
}

function openEdit(user) {
  editing.value = user
  Object.assign(form, {
    username: user.username,
    full_name: user.full_name || '',
    email: user.email,
    password: '',
    role: user.role === 'admin' ? 'admin' : 'user',
    faculty_id: user.faculty_id || '',
    is_active: user.is_active
  })
  modalError.value = ''
  showModal.value = true
}

function closeModal() {
  if (!saving.value) showModal.value = false
}

async function save() {
  modalError.value = ''
  const isAdminRole = !editing.value || form.role === 'admin'
  if (isAdminRole && !form.faculty_id) {
    modalError.value = 'Выберите факультет для администратора'
    return
  }

  saving.value = true
  try {
    if (editing.value) {
      const payload = {
        full_name: form.full_name.trim() || null,
        email: form.email.trim(),
        role: form.role,
        faculty_id: form.role === 'admin' ? Number(form.faculty_id) : null,
        is_active: form.is_active
      }
      if (form.password) payload.new_password = form.password
      await universityService.updateUser(editing.value.id, payload)
      notify.success('Данные пользователя сохранены')
    } else {
      await universityService.createFacultyAdmin({
        username: form.username.trim(),
        email: form.email.trim(),
        full_name: form.full_name.trim() || null,
        password: form.password,
        faculty_id: Number(form.faculty_id)
      })
      notify.success('Администратор факультета создан')
    }
    showModal.value = false
    await load()
  } catch (e) {
    modalError.value = extractErrors(e).message
  } finally {
    saving.value = false
  }
}

async function askDelete(user) {
  const done = await notify.confirm({
    title: 'Удалить пользователя?',
    message: `Аккаунт «${user.username}» будет удалён. Созданные им карточки останутся в каталоге.`,
    confirmText: 'Удалить',
    danger: true,
    action: () => universityService.deleteUser(user.id)
  })
  if (!done) return
  notify.success(`Пользователь «${user.username}» удалён`)
  await load()
}

onMounted(async () => {
  try {
    faculties.value = await universityService.getFaculties()
  } catch (e) { /* без списка факультетов форма покажет пустой выбор */ }
  await load()
})
</script>
