const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

async function httpGet(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: { 'Accept': 'application/json' } })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed: ${res.status} ${res.statusText} - ${text}`)
  }
  return res.json()
}

export const api = {
  getBranches: () => httpGet('/api/v1/branches'),
  getBranch: (id) => httpGet(`/api/v1/branches/${id}`),
  getCameras: () => httpGet('/api/v1/cameras'),
  getCamera: (id) => httpGet(`/api/v1/cameras/${id}`),
  getCamerasByBranch: (id) => httpGet(`/api/v1/branches/${id}/cameras`),
}

export function buildStreamUrl(streamName) {
  const tpl = import.meta.env.VITE_GO2RTC_STREAM_URL_TEMPLATE
  const base = import.meta.env.VITE_GO2RTC_BASE_URL || ''
  if (tpl) return tpl.replace('{stream}', encodeURIComponent(streamName))
  if (base) return `${base.replace(/\/$/, '')}/stream.html?src=${encodeURIComponent(streamName)}`
  // Fallback to relative path if served via same origin reverse proxy
  return `/go2rtc/stream.html?src=${encodeURIComponent(streamName)}`
}
