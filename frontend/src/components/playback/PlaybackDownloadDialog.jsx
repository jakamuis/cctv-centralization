/**
 * PlaybackDownloadDialog.jsx
 *
 * Modal dialog for downloading a recording clip.
 *
 * Props:
 *   open        {boolean}
 *   onClose     {function}
 *   deviceId    {string}
 *   channel     {number}
 *   startTime   {Date}
 *   endTime     {Date}
 *   deviceName  {string}
 */

import { useState, useEffect, useRef } from 'react'
import { getAuthToken } from '../../api'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatElapsed(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export default function PlaybackDownloadDialog({
  open,
  onClose,
  deviceId,
  channel,
  startTime,
  endTime,
  deviceName,
}) {
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState('')
  const [receivedBytes, setReceivedBytes] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef(null)

  useEffect(() => {
    if (!open) {
      setDownloading(false)
      setError('')
      setReceivedBytes(0)
      setElapsed(0)
    }
  }, [open])

  useEffect(() => {
    if (downloading) {
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [downloading])

  if (!open) return null

  const durationSeconds = startTime && endTime
    ? (new Date(endTime).getTime() - new Date(startTime).getTime()) / 1000
    : 0
  const durationStr = durationSeconds > 0
    ? `${Math.floor(durationSeconds / 3600)}h ${Math.floor((durationSeconds % 3600) / 60)}m ${Math.floor(durationSeconds % 60)}s`
    : '—'

  const handleDownload = async () => {
    setDownloading(true)
    setError('')
    setReceivedBytes(0)
    setElapsed(0)

    try {
      const token = getAuthToken()
      const res = await fetch(`${API_BASE}/playback/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          device_id: deviceId,
          channel,
          start_time: startTime instanceof Date ? startTime.toISOString() : startTime,
          end_time: endTime instanceof Date ? endTime.toISOString() : endTime,
        }),
      })

      if (!res.ok) {
        let errMsg = `HTTP ${res.status}`
        try {
          const json = await res.json()
          errMsg = json.detail || json.message || errMsg
        } catch {
          const text = await res.text().catch(() => '')
          if (text) errMsg = text
        }
        throw new Error(errMsg)
      }

      // Stream response body to track progress
      const reader = res.body.getReader()
      const chunks = []
      let total = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        chunks.push(value)
        total += value.length
        setReceivedBytes(total)
      }

      // Get filename from Content-Disposition
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="?([^"]+)"?/)
      const filename = match ? match[1] : `recording_ch${channel}.mp4`

      // Trigger file save
      const blob = new Blob(chunks, { type: 'video/mp4' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      onClose?.()
    } catch (e) {
      setError(e.message || 'Download failed')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div style={styles.backdrop} onClick={e => e.target === e.currentTarget && onClose?.()}>
      <div style={styles.dialog}>
        <div style={styles.header}>
          <span style={styles.title}>⬇ Download Recording</span>
          <button style={styles.closeBtn} onClick={onClose} disabled={downloading}>✕</button>
        </div>

        <div style={styles.body}>
          <InfoRow label="Device" value={deviceName || deviceId} />
          <InfoRow label="Channel" value={`Channel ${channel}`} />
          <InfoRow label="Start" value={startTime ? new Date(startTime).toLocaleString() : '—'} />
          <InfoRow label="End" value={endTime ? new Date(endTime).toLocaleString() : '—'} />
          <InfoRow label="Duration" value={durationStr} />

          {downloading && (
            <div style={styles.progressBox}>
              <div style={styles.progressBar}>
                <div style={styles.progressFill} />
              </div>
              <div style={styles.progressStats}>
                <span>{formatBytes(receivedBytes)} received</span>
                <span>{formatElapsed(elapsed)} elapsed</span>
              </div>
            </div>
          )}

          {!downloading && !error && (
            <div style={styles.note}>
              The server streams the recording directly from the NVR. Your browser download will start and show progress as data arrives.
            </div>
          )}

          {error && (
            <div style={styles.error}>{error}</div>
          )}
        </div>

        <div style={styles.footer}>
          <button style={styles.cancelBtn} onClick={onClose} disabled={downloading}>
            Cancel
          </button>
          <button
            style={{ ...styles.downloadBtn, opacity: downloading ? 0.6 : 1 }}
            onClick={handleDownload}
            disabled={downloading}
          >
            {downloading ? '⏳ Downloading…' : '⬇ Download MP4'}
          </button>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
      <span style={{ color: '#6b7280', fontSize: '0.8rem', minWidth: 70 }}>{label}</span>
      <span style={{ color: '#f9fafb', fontSize: '0.8rem', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

const shimmer = `
@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}
`
if (typeof document !== 'undefined') {
  const style = document.createElement('style')
  style.textContent = shimmer
  document.head.appendChild(style)
}

const styles = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  dialog: {
    backgroundColor: '#1f2937',
    borderRadius: 12,
    border: '1px solid #374151',
    width: 420,
    maxWidth: '90vw',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid #374151',
  },
  title: {
    color: '#f9fafb',
    fontSize: '1rem',
    fontWeight: 700,
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#9ca3af',
    cursor: 'pointer',
    fontSize: '1rem',
  },
  body: {
    padding: '16px 20px',
  },
  progressBox: {
    marginTop: 14,
  },
  progressBar: {
    width: '100%',
    height: 6,
    backgroundColor: '#374151',
    borderRadius: 3,
    overflow: 'hidden',
    position: 'relative',
  },
  progressFill: {
    position: 'absolute',
    top: 0,
    left: 0,
    height: '100%',
    width: '40%',
    backgroundColor: '#3b82f6',
    borderRadius: 3,
    animation: 'shimmer 1.4s ease-in-out infinite',
  },
  progressStats: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: 6,
    color: '#9ca3af',
    fontSize: '0.75rem',
  },
  note: {
    marginTop: 12,
    padding: '8px 12px',
    backgroundColor: '#111827',
    borderRadius: 6,
    color: '#9ca3af',
    fontSize: '0.75rem',
    border: '1px solid #374151',
  },
  error: {
    marginTop: 8,
    padding: '8px 12px',
    backgroundColor: '#450a0a',
    borderRadius: 6,
    color: '#fca5a5',
    fontSize: '0.75rem',
    border: '1px solid #7f1d1d',
  },
  footer: {
    display: 'flex',
    gap: 8,
    justifyContent: 'flex-end',
    padding: '12px 20px',
    borderTop: '1px solid #374151',
  },
  cancelBtn: {
    backgroundColor: '#374151',
    color: '#d1d5db',
    border: 'none',
    borderRadius: 6,
    padding: '8px 16px',
    fontSize: '0.875rem',
    cursor: 'pointer',
  },
  downloadBtn: {
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '8px 16px',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
}
