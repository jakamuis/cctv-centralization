/**
 * Centralized API client
 *
 * VITE_API_BASE_URL = http://localhost:8000/api/v1
 *
 * All paths passed to httpGet/httpPost/httpDelete must be RELATIVE,
 * e.g. "/auth/me", "/discovery/nvrs", "/branches"
 * Never include /api/v1 in the path — it is already in the base URL.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

// ============================================
// Token helpers
// ============================================

export function getAuthToken() {
  return localStorage.getItem('auth_token')
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('auth_token', token)
  } else {
    localStorage.removeItem('auth_token')
  }
}

export function clearAuthToken() {
  localStorage.removeItem('auth_token')
}

function getAuthHeaders() {
  const token = getAuthToken()
  const headers = {
    Accept: 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

// ============================================
// Core HTTP helpers
// ============================================

async function httpGet(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: getAuthHeaders(),
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

  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: body !== undefined ? JSON.stringify(body) : null,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed: ${res.status} ${res.statusText} - ${text}`)
  }
  return res.json()
}

async function httpPut(path, body) {
  const headers = getAuthHeaders()
  headers['Content-Type'] = 'application/json'

  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers,
    body: body !== undefined ? JSON.stringify(body) : null,
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
    headers: getAuthHeaders(),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed: ${res.status} ${res.statusText} - ${text}`)
  }
  if (res.status === 204) return null
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

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Accept: 'application/json',
      },
      body: formData,
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`Login failed: ${res.status} ${res.statusText} - ${text}`)
    }

    const data = await res.json()
    console.log('authApi.login: received data:', data)
    if (data.access_token) {
      setAuthToken(data.access_token)
      console.log('authApi.login: stored access_token')
    }
    return data
  },

  logout: async () => {
    try {
      await httpPost('/auth/logout')
    } finally {
      clearAuthToken()
    }
  },

  getCurrentUser: async () => {
    return httpGet('/auth/me')
  },
}

// ============================================
// API Client (branches, cameras, streams)
// ============================================

// Avoid duplicate start requests per camera concurrently
const pendingStart = new Map()

export const api = {
  getBranches: async () => {
    const response = await httpGet('/branches')
    return response.items || response || []
  },
  getBranch: (id) => httpGet(`/branches/${id}`),
  getCameras: async () => {
    const response = await httpGet('/cameras')
    return response.items || response || []
  },
  getCamera: (id) => httpGet(`/cameras/${id}`),
  getCamerasByBranch: async (id) => {
    const response = await httpGet(`/branches/${id}/cameras`)
    return response.items || response || []
  },
  startLive: (cameraId, { viewerId } = {}) => {
    if (!cameraId) throw new Error('cameraId required')
    if (pendingStart.has(cameraId)) return pendingStart.get(cameraId)
    const p = httpPost(`/streams/live/${cameraId}`, viewerId ? { viewer_id: viewerId } : undefined)
      .finally(() => pendingStart.delete(cameraId))
    pendingStart.set(cameraId, p)
    return p
  },
  stopLive: (cameraId) => {
    if (!cameraId) return Promise.resolve({ stopped: false })
    return httpDelete(`/streams/live/${cameraId}`)
  },
}

// ============================================
// Discovery API (Phase 7B)
// ============================================

export const discoveryApi = {
  getNvrs: () => httpGet('/discovery/nvrs'),
  getChannels: (nvrId) => httpGet(`/discovery/nvrs/${nvrId}/channels`),
  // Register channel with go2rtc and get back stream_name
  startChannelStream: (nvrId, channelId) =>
    httpPost(`/discovery/nvrs/${nvrId}/channels/${channelId}/stream`),
}

// ============================================
// Devices API
// ============================================

export const devicesApi = {
  list: (params = {}) => {
    const q = new URLSearchParams()
    if (params.site_id) q.set('site_id', params.site_id)
    if (params.status)  q.set('status', params.status)
    const qs = q.toString()
    return httpGet(`/devices/${qs ? `?${qs}` : ''}`)
  },
  create: (data) => httpPost('/devices/', data),
  update: (id, data) => httpPut(`/devices/${id}`, data),
  remove: (id) => httpDelete(`/devices/${id}`),
}

// ============================================
// Sites API
// ============================================

export const sitesApi = {
  getSites: () => httpGet('/sites'),
  getSite: (id) => httpGet(`/sites/${id}`),
}

// ============================================
// Stream URL helpers
// ============================================

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
    sessionStorage.setItem(
      key,
      crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    )
  }
  return sessionStorage.getItem(key)
}

// ============================================
// Playback API (Phase 9)
// ============================================

export const playbackApi = {
  /**
   * Search for recording segments on a device/channel within a time window.
   */
  searchRecordings: (deviceId, channel, startTime, endTime) =>
    httpPost('/playback/search', {
      device_id: deviceId,
      channel,
      start_time: startTime instanceof Date ? startTime.toISOString() : startTime,
      end_time: endTime instanceof Date ? endTime.toISOString() : endTime,
    }),

  /**
   * Get timeline blocks (recording + gap) for a device/channel/window.
   */
  getTimeline: (deviceId, channel, startTime, endTime) =>
    httpPost('/playback/timeline', {
      device_id: deviceId,
      channel,
      start_time: startTime instanceof Date ? startTime.toISOString() : startTime,
      end_time: endTime instanceof Date ? endTime.toISOString() : endTime,
    }),

  /**
   * Create a playback session. Returns session_id, stream_name, stream_url.
   */
  createSession: (deviceId, channel, startTime, endTime) =>
    httpPost('/playback/session', {
      device_id: deviceId,
      channel,
      start_time: startTime instanceof Date ? startTime.toISOString() : startTime,
      end_time: endTime instanceof Date ? endTime.toISOString() : endTime,
    }),

  /**
   * Extend session TTL (heartbeat / keep-alive).
   */
  heartbeat: (sessionId) =>
    httpPost(`/playback/session/${sessionId}/heartbeat`),

  /**
   * Destroy a playback session and clean up go2rtc stream.
   */
  deleteSession: (sessionId) =>
    httpDelete(`/playback/session/${sessionId}`),

  /**
   * Initiate a recording clip download.
   * Returns a URL to trigger the browser download.
   */
  getDownloadUrl: (deviceId, channel, startTime, endTime) => {
    const token = getAuthToken()
    const params = new URLSearchParams({
      device_id: deviceId,
      channel: String(channel),
      start_time: startTime instanceof Date ? startTime.toISOString() : startTime,
      end_time: endTime instanceof Date ? endTime.toISOString() : endTime,
    })
    if (token) params.set('token', token)
    return `${API_BASE}/playback/download?${params.toString()}`
  },
}
