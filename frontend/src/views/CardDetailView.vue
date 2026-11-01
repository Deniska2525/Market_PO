<template>
  <div class="u-page u-page--narrow">
    <div v-if="loading" class="u-state">Загрузка…</div>
    <div v-else-if="error" class="u-state">
      <p>{{ error }}</p>
      <router-link to="/cards" class="btn btn-secondary">← В каталог</router-link>
    </div>

    <template v-else-if="card">
      <router-link to="/cards" class="back">← Каталог разработок</router-link>

      <div v-if="card.status !== 'published'" class="u-notice">
        Это черновик: карточку видят только администратор факультета и суперадмин. Посетители её не увидят.
      </div>

      <header class="head">
        <div class="u-chips">
          <router-link class="u-chip" :to="{ path: '/cards', query: { faculty_id: card.faculty_id } }">{{ card.faculty_name }}</router-link>
          <span v-if="card.readiness" class="u-badge u-badge--info">{{ READINESS_LABELS[card.readiness] }}</span>
        </div>
        <h1>{{ card.title }}</h1>
        <p class="summary">{{ card.summary }}</p>
        <div v-if="card.tags.length" class="u-chips">
          <router-link v-for="t in card.tags" :key="t" class="u-chip" :to="{ path: '/cards', query: { tag: t } }">{{ t }}</router-link>
        </div>
        <div class="u-actions cta">
          <button v-if="card.status === 'published'" class="btn btn-primary" @click="openForm">✉️ Оставить заявку</button>
          <router-link v-if="card.can_manage" :to="`/manage/cards/${card.id}`" class="btn btn-secondary">✏️ Редактировать</router-link>
        </div>
      </header>

      <img v-if="card.cover_url" :src="apiUrl(card.cover_url)" :alt="card.title" class="cover">

      <section v-if="card.description" class="block">
        <h2>Описание</h2>
        <!-- HTML очищен на сервере белым списком тегов (backend/app/sanitize.py) -->
        <div class="rich" v-html="card.description"></div>
      </section>

      <section v-if="card.gallery_urls.length" class="block">
        <h2>Изображения</h2>
        <div class="gallery">
          <img
            v-for="(url, i) in card.gallery_urls"
            :key="url"
            :src="apiUrl(url)"
            :alt="`${card.title}, изображение ${i + 1}`"
            loading="lazy"
            @click="lightbox = i"
          >
        </div>
      </section>

      <section v-if="hasContacts" class="block">
        <h2>Контакты</h2>
        <dl class="contacts">
          <template v-if="card.contact_name"><dt>Контактное лицо</dt><dd>{{ card.contact_name }}</dd></template>
          <template v-if="card.contact_email">
            <dt>Email</dt><dd><a :href="`mailto:${card.contact_email}`">{{ card.contact_email }}</a></dd>
          </template>
          <template v-if="card.contact_phone">
            <dt>Телефон</dt><dd><a :href="`tel:${card.contact_phone}`">{{ card.contact_phone }}</a></dd>
          </template>
          <template v-if="card.website">
            <dt>Сайт</dt>
            <dd><a :href="card.website" target="_blank" rel="noopener noreferrer">{{ card.website }}</a></dd>
          </template>
        </dl>
      </section>

      <!-- Просмотр изображения -->
      <div v-if="lightbox !== null" ref="lightboxPanel" class="lightbox" tabindex="-1" role="dialog" aria-modal="true" aria-label="Просмотр изображения" @click="lightbox = null">
        <button v-if="lightbox > 0" class="nav prev" aria-label="Предыдущее" @click.stop="lightbox -= 1">‹</button>
        <img :src="apiUrl(card.gallery_urls[lightbox])" alt="">
        <button v-if="lightbox < card.gallery_urls.length - 1" class="nav next" aria-label="Следующее" @click.stop="lightbox += 1">›</button>
        <button class="close" aria-label="Закрыть" @click.stop="lightbox = null">×</button>
      </div>

      <!-- Заявка -->
      <div v-if="showForm" class="modal-overlay" @mousedown.self="closeForm">
        <div ref="formPanel" class="modal-content inquiry" role="dialog" aria-modal="true" aria-labelledby="inquiry-title" tabindex="-1">
          <h3 id="inquiry-title">Заявка по разработке</h3>
          <p class="u-muted">«{{ card.title }}». Сотрудники факультета свяжутся с вами по указанным контактам.</p>

          <form @submit.prevent="submit">
            <div class="u-row2">
              <div class="form-group">
                <label for="inq-name">Ваше имя *</label>
                <input id="inq-name" v-model="form.name" type="text" maxlength="100" required>
              </div>
              <div class="form-group">
                <label for="inq-email">Email *</label>
                <input id="inq-email" v-model="form.email" type="email" required>
              </div>
            </div>
            <div class="u-row2">
              <div class="form-group">
                <label for="inq-phone">Телефон</label>
                <input id="inq-phone" v-model="form.phone" type="tel" maxlength="30">
              </div>
              <div class="form-group">
                <label for="inq-org">Организация</label>
                <input id="inq-org" v-model="form.organization" type="text" maxlength="150">
              </div>
            </div>
            <div class="form-group">
              <label for="inq-message">Что вас интересует *</label>
              <textarea id="inq-message" v-model="form.message" rows="5" minlength="5" maxlength="2000" required
                placeholder="Опишите задачу и формат сотрудничества"></textarea>
            </div>

            <!-- Ловушка для ботов: человек это поле не видит и не заполняет -->
            <div class="hp" aria-hidden="true">
              <label>Сайт <input v-model="form.website" type="text" tabindex="-1" autocomplete="off"></label>
            </div>

            <div v-if="formError" class="u-alert" role="alert">{{ formError }}</div>

            <div class="u-form-actions">
              <button type="submit" class="btn btn-primary" :disabled="sending">{{ sending ? 'Отправка…' : 'Отправить заявку' }}</button>
              <button type="button" class="btn btn-secondary" :disabled="sending" @click="closeForm">Отмена</button>
            </div>
          </form>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import universityService, { apiUrl } from '../services/university'
import { useAuthStore } from '../stores/auth'
import { useNotify } from '../composables/useNotify'
import { useDialogA11y } from '../composables/useDialogA11y'
import { READINESS_LABELS, extractErrors } from '../utils/format'

const route = useRoute()
const authStore = useAuthStore()
const notify = useNotify()

const card = ref(null)
const loading = ref(true)
const error = ref('')
const lightbox = ref(null)
const showForm = ref(false)
const sending = ref(false)
const formError = ref('')
const form = reactive({ name: '', email: '', phone: '', organization: '', message: '', website: '' })

const lightboxPanel = ref(null)
const formPanel = ref(null)

const hasContacts = computed(() =>
  !!(card.value && (card.value.contact_name || card.value.contact_email || card.value.contact_phone || card.value.website))
)

// Доступность окон: Esc, фокус не уходит за пределы, возврат фокуса на кнопку
useDialogA11y({ panel: lightboxPanel, active: computed(() => lightbox.value !== null), onEscape: () => { lightbox.value = null } })
useDialogA11y({ panel: formPanel, active: computed(() => showForm.value), onEscape: () => { if (!sending.value) showForm.value = false } })

async function load() {
  loading.value = true
  error.value = ''
  card.value = null
  lightbox.value = null
  try {
    card.value = await universityService.getCard(route.params.id)
  } catch (e) {
    error.value = e?.response?.status === 404
      ? 'Карточка не найдена или ещё не опубликована.'
      : extractErrors(e).message
  } finally {
    loading.value = false
  }
}

function openForm() {
  formError.value = ''
  if (authStore.user) {
    if (!form.name) form.name = authStore.user.full_name || authStore.user.username || ''
    if (!form.email) form.email = authStore.user.email || ''
  }
  showForm.value = true
}

function closeForm() {
  if (!sending.value) showForm.value = false
}

async function submit() {
  formError.value = ''
  if (!form.name.trim() || !form.email.trim() || form.message.trim().length < 5) {
    formError.value = 'Заполните имя, email и сообщение (не короче 5 символов)'
    return
  }
  sending.value = true
  try {
    await universityService.createInquiry(card.value.id, {
      name: form.name,
      email: form.email,
      phone: form.phone || null,
      organization: form.organization || null,
      message: form.message,
      website: form.website || null
    })
    notify.success('Сотрудники факультета свяжутся с вами по указанным контактам.', { title: 'Заявка отправлена' })
    form.message = ''
    showForm.value = false
  } catch (e) {
    formError.value = extractErrors(e).message
    notify.error(formError.value)
  } finally {
    sending.value = false
  }
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<style scoped>
.back { display: inline-block; margin-bottom: 1rem; color: var(--primary-color); text-decoration: none; }
.head { margin-bottom: 1.5rem; display: flex; flex-direction: column; gap: 0.7rem; }
.head h1 { color: var(--text-primary); font-size: 1.9rem; line-height: 1.25; }
.summary { color: var(--text-secondary); font-size: 1.08rem; line-height: 1.55; }
.cta { margin-top: 0.4rem; }
.cover { width: 100%; max-height: 380px; object-fit: cover; border-radius: 14px; border: 1px solid var(--border-color); margin-bottom: 1.5rem; }

.block { margin-top: 2rem; }
.block h2 { color: var(--text-primary); font-size: 1.3rem; margin-bottom: 0.8rem; }

.rich { color: var(--text-primary); line-height: 1.7; }
.rich :deep(h2) { font-size: 1.25rem; margin: 1rem 0 0.4rem; }
.rich :deep(h3) { font-size: 1.1rem; margin: 0.9rem 0 0.3rem; }
.rich :deep(p) { margin: 0.5rem 0; }
.rich :deep(ul), .rich :deep(ol) { margin: 0.5rem 0; padding-left: 1.5rem; }
.rich :deep(blockquote) { margin: 0.7rem 0; padding-left: 1rem; border-left: 3px solid var(--primary-color); color: var(--text-secondary); }
.rich :deep(a) { color: var(--primary-color); text-decoration: underline; }
.rich :deep(img) { max-width: 100%; }

.gallery { display: flex; gap: 0.7rem; overflow-x: auto; padding-bottom: 0.4rem; }
.gallery img { height: 180px; border-radius: 10px; border: 1px solid var(--border-color); cursor: zoom-in; flex-shrink: 0; }

.contacts { display: grid; grid-template-columns: max-content 1fr; gap: 0.5rem 1.2rem; }
.contacts dt { color: var(--text-muted); }
.contacts dd { color: var(--text-primary); word-break: break-word; }
.contacts a { color: var(--primary-color); }

.inquiry { max-width: 640px; }
.inquiry h3 { margin-bottom: 0.3rem; }
.inquiry > .u-muted { margin-bottom: 1rem; }
.hp { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }

.lightbox { position: fixed; inset: 0; z-index: 2000; background: rgba(0, 0, 0, 0.88); display: flex; align-items: center; justify-content: center; cursor: zoom-out; }
.lightbox img { max-width: 92vw; max-height: 90vh; border-radius: 8px; }
.lightbox .nav, .lightbox .close { position: absolute; background: rgba(255, 255, 255, 0.18); color: #fff; border: none; cursor: pointer; border-radius: 8px; }
.lightbox .nav { top: 50%; transform: translateY(-50%); font-size: 2.5rem; padding: 0.2rem 1rem; }
.lightbox .prev { left: 1rem; }
.lightbox .next { right: 1rem; }
.lightbox .close { top: 1rem; right: 1rem; font-size: 1.8rem; padding: 0 0.8rem; }
</style>
