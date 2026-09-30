const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

function getToken() {
  return localStorage.getItem('rm_token')
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.message || `Request failed: ${res.status}`)
  }
  const contentType = res.headers.get('content-type') || ''
  return contentType.includes('application/json') ? res.json() : res.text()
}

export const api = {
  register: (email, password, displayName) =>
    request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, displayName }) }),

  login: (email, password) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),

  listDocuments: () => request('/api/documents'),

  uploadDocument: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    const token = getToken()
    const res = await fetch(`${BASE_URL}/api/documents/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },

  deleteDocument: (id) => request(`/api/documents/${id}`, { method: 'DELETE' }),

  sendChat: (message, conversationId, documentIds) =>
    request('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversationId, documentIds }),
    }),

  listConversations: () => request('/api/conversations'),

  getConversationMessages: (id) => request(`/api/conversations/${id}`),
}

export function setToken(token) {
  localStorage.setItem('rm_token', token)
}

export function clearToken() {
  localStorage.removeItem('rm_token')
}

export function isLoggedIn() {
  return !!getToken()
}
