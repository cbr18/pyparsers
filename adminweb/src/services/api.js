import axios from 'axios'

const api = axios.create({
  baseURL: '/api/admin-service',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Добавляем токен из localStorage при инициализации
const token = localStorage.getItem('token')
if (token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

export const fetchCarByUuid = async (uuid) => {
  const response = await axios.get(`/api/cars/uuid/${encodeURIComponent(uuid)}`)
  if (response?.data?.data) {
    return response.data.data
  }
  return response.data
}

export const applyTelegramIdsToBot = () => api.post('/integrations/adminbot/apply-tgids')

export const triggerFullParsing = (source) =>
  api.post('/admin/update/full', { source })

export const triggerIncrementalParsing = (source, lastN) =>
  api.post('/admin/update/incremental', lastN ? { source, lastN } : { source })

export default api







