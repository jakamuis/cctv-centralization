const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

// ============================================
// Authentication Token Management
// ============================================

const TOKEN_KEY = 'auth_token'

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function isAuthenticated() {
  return !!getAuthToken()
}

// ============================================
// HTTP Client with Authentication
// ============================================

function getAuthHeaders() {
  const headers = { 'Accept': 'application/json' }
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function httpGet(path) {
  const res = await fetch(`${API_BASE}${path}`, { 
    headers: getAuthHeaders() 
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed: ${res.status} ${res.statusText} - ${text}`)
  }
  return res.json()
}

async function httpPost(path, body) {
  const headers = getAuthHeaders()
  headers['Content-Type'] = 'application/json'
  
  const res = await fetch(`${API_BASE}${path}`,
    {
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : null,
    })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed: ${res.status} ${res.statusText} - ${text}`)
  }
  return res.json()
}

async function httpDelete(path) {
  const res = await fetch(`${API_BASE}${path}`, { 
    method: 'DELETE', 
    headers: getAuthHeaders() 
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed: ${res.status} ${res.statusText} - ${text}`)
  }
  return res.json()
}

// ============================================
// Authentication API
// ============================================

export const authApi = {
  login: async (username, password) => {
    // OAuth2PasswordRequestForm expects form data, not JSON
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
      body: formData,
    })
    
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`Login failed: ${res.status} ${res.statusText} - ${text}`)
    }
    
    const data = await res.json()
    // Store the token
    if (data.access_token) {
      setAuthToken(data.access_token)
    }
    return data
  },
  
  logout: async () => {
    try {
      await httpPost('/api/v1/auth/logout')
    } finally {
      clearAuthToken()
    }
  },
  
  getCurrentUser: async () => {
    return httpGet('/api/v1/auth/me')
  },
}

// ============================================
// API Client (with authentication)
// ============================================

// Avoid duplicate start requests per camera concurrently
const pendingStart = new Map()

export const api = {
  getBranches: async () => {
    const response = await httpGet('/api/v1/branches')
    return response.items || []
  },
  getBranch: (id) => httpGet(`/api/v1/branches/${id}`),
  getCameras: async () => {
    const response = await httpGet('/api/v1/cameras')
    return response.items || []
  },
  getCamera: (id) => httpGet(`/api/v1/cameras/${id}`),
  getCamerasByBranch: async (id) => {
    const response = await httpGet(`/api/v1/branches/${id}/cameras`)
    return response.items || []
  },
  startLive: (cameraId, { viewerId } = {}) => {
    if (!cameraId) throw new Error('cameraId required')
    if (pendingStart.has(cameraId)) return pendingStart.get(cameraId)
    const p = httpPost(`/api/v1/streams/live/${cameraId}`, viewerId ? { viewer_id: viewerId } : undefined)
      .finally(() => pendingStart.delete(cameraId))
    pendingStart.set(cameraId, p)
    return p
  },
  stopLive: (cameraId) => {
    if (!cameraId) return Promise.resolve({ stopped: false })
    return httpDelete(`/api/v1/streams/live/${cameraId}`)
  },
}

// ============================================
// Discovery API (Phase 7B — no auth required temporarily)
// ============================================

export const discoveryApi = {
  getNvrs: () => httpGet('/api/v1/discovery/nvrs'),
  getChannels: (nvrId) => httpGet(`/api/v1/discovery/nvrs/${nvrId}/channels`),
  // Register channel with go2rtc and get back stream_name
  startChannelStream: (nvrId, channelId) =>
    httpPost(`/api/v1/discovery/nvrs/${nvrId}/channels/${channelId}/stream`),
}

export function buildStreamUrl(streamName) {
  const tpl = import.meta.env.VITE_GO2RTC_STREAM_URL_TEMPLATE
  const base = import.meta.env.VITE_GO2RTC_BASE_URL || ''
  if (tpl) return tpl.replace('{stream}', encodeURIComponent(streamName))
  if (base) return `${base.replace(/\/$/, '')}/stream.html?src=${encodeURIComponent(streamName)}`
  // Fallback to relative path if served via same origin reverse proxy
  return `/go2rtc/stream.html?src=${encodeURIComponent(streamName)}`
}

export function getViewerId() {
  // stable per-tab viewer id to reduce duplicate sessions
  const key = 'viewer_id'
  if (!sessionStorage.getItem(key)) {
    sessionStorage.setItem(key, crypto.randomUUID ? crypto.randomUUID() : String(Date.now()))
  }
  return sessionStorage.getItem(key)
}
