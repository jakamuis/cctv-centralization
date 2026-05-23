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

import React, { useState } from 'react'
import { playbackApi, getAuthToken } from '../../api'

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
    try {
      // POST to download endpoint — backend streams the file
      const token = getAuthToken()
      const res = await fetch('/api/v1/playback/download', {
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
        const text = await res.text().catch(() => '')
        throw new Error(`Download failed: ${res.status} — ${text}`)
      }

      // Get filename from Content-Disposition header
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="?([^"]+)"?/)
      const filename = match ? match[1] : `recording_ch${channel}.mp4`

      // Stream to blob and trigger download
      const blob = await res.blob()
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
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div style={styles.body}>
          <InfoRow label="Device" value={deviceName || deviceId} />
          <InfoRow label="Channel" value={`Channel ${channel}`} />
          <InfoRow
            label="Start"
            value={startTime ? new Date(startTime).toLocaleString() : '—'}
          />
          <InfoRow
            label="End"
            value={endTime ? new Date(endTime).toLocaleString() : '—'}
          />
          <InfoRow label="Duration" value={durationStr} />

          <div style={styles.note}>
            ⚠ The recording will be streamed directly from the NVR.
            Large clips may take a while to download.
          </div>

          {error && (
            <div style={styles.error}>{error}</div>
          )}
        </div>

        <div style={styles.footer}>
          <button style={styles.cancelBtn} onClick={onClose} disabled={downloading}>
            Cancel
          </button>
          <button
            style={{
              ...styles.downloadBtn,
              opacity: downloading ? 0.6 : 1,
            }}
            onClick={handleDownload}
            disabled={downloading}
          >
            {downloading ? '⟳ Downloading…' : '⬇ Download MP4'}
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
