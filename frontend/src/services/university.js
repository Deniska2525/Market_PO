import api from './api'

// Абсолютный адрес ресурса backend по пути вида /media/5/file (для <img>)
export function apiUrl(path) {
  return path ? `${api.defaults.baseURL}${path}` : ''
}

// Клиент API витрины разработок. Ошибки не глотаем: вызывающий код показывает их
// через notify.fail() или extractErrors() из utils/format.js.
class UniversityService {
  // --- Факультеты ---
  async getFaculties() {
    return (await api.get('/faculties')).data
  }

  async createFaculty(payload) {
    return (await api.post('/faculties', payload)).data
  }

  async updateFaculty(id, payload) {
    return (await api.put(`/faculties/${id}`, payload)).data
  }

  async deleteFaculty(id) {
    return (await api.delete(`/faculties/${id}`)).data
  }

  // --- Теги ---
  async getTags(params = {}) {
    return (await api.get('/tags', { params })).data
  }

  async deleteTag(id) {
    return (await api.delete(`/tags/${id}`)).data
  }

  // --- Карточки: публичные ---
  async getCards(params = {}) {
    return (await api.get('/cards', { params })).data
  }

  async getCard(id) {
    return (await api.get(`/cards/${id}`)).data
  }

  async aiSearch(query) {
    return (await api.post('/ai-search/', { query })).data
  }

  // --- Карточки: управление (сотрудники) ---
  async manageCards(params = {}) {
    return (await api.get('/cards/manage', { params })).data
  }

  async manageStats() {
    return (await api.get('/cards/manage/stats')).data
  }

  async createCard(payload) {
    return (await api.post('/cards', payload)).data
  }

  async updateCard(id, payload) {
    return (await api.put(`/cards/${id}`, payload)).data
  }

  async setCardStatus(id, status) {
    return (await api.put(`/cards/${id}/status`, { status })).data
  }

  async deleteCard(id) {
    return (await api.delete(`/cards/${id}`)).data
  }

  // --- Заявки ---
  async createInquiry(cardId, payload) {
    return (await api.post(`/cards/${cardId}/inquiries`, payload)).data
  }

  async getInquiries(params = {}) {
    return (await api.get('/inquiries', { params })).data
  }

  async setInquiryStatus(id, status) {
    return (await api.put(`/inquiries/${id}/status`, { status })).data
  }

  async deleteInquiry(id) {
    return (await api.delete(`/inquiries/${id}`)).data
  }

  // --- Медиатека ---
  async listMedia(params = {}) {
    return (await api.get('/media', { params })).data
  }

  // Файл уходит «сырым» телом: так backend пишет его на диск потоком, а не держит в памяти.
  // Content-Type задаём явно, иначе axios применит JSON по умолчанию.
  async uploadMedia(file, kind, onProgress) {
    const { data } = await api.post('/media', file, {
      params: { filename: file.name, kind },
      headers: { 'Content-Type': 'application/octet-stream' },
      timeout: 0,
      onUploadProgress: event => {
        if (onProgress && event.total) onProgress(Math.round((event.loaded / event.total) * 100))
      }
    })
    return data
  }

  async deleteMedia(id) {
    return (await api.delete(`/media/${id}`)).data
  }

  // --- Администрирование (суперадмин) ---
  async getAdminStats() {
    return (await api.get('/admin/stats')).data
  }

  async getUsers(params = {}) {
    return (await api.get('/admin/users', { params })).data
  }

  async createFacultyAdmin(payload) {
    return (await api.post('/admin/users', payload)).data
  }

  async updateUser(id, payload) {
    return (await api.put(`/admin/users/${id}`, payload)).data
  }

  async deleteUser(id) {
    return (await api.delete(`/admin/users/${id}`)).data
  }
}

export default new UniversityService()
