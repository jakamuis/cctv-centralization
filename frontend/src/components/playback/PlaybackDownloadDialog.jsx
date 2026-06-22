import { useState, useEffect, useRef } from 'react'
import { getAuthToken } from '../../api'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function formatCountdown(remaining) {
  if (remaining <= 0) return 'almost done…'
  const m = Math.floor(remaining / 60)
  const s = Math.floor(remaining % 60)
  return m > 0 ? `~${m}m ${s}s remaining` : `~${s}s remaining`
}

export default function PlaybackDownloadDialog({
  open,
  onClose,
  deviceId,
  channel,
  startTime,
  endTime,
  deviceName,
  session,
}) {
  const [phase, setPhase]             = useState('idle')   // idle | connecting | downloading | done
  const [error, setError]             = useState('')
  const [receivedBytes, setReceivedBytes] = useState(0)
  const [elapsed, setElapsed]         = useState(0)
  const [cacheStatus, setCacheStatus] = useState(null)   // null | {file_complete, file_size_mb}
  const timerRef = useRef(null)

  // Check server cache status when dialog opens with an active session
  useEffect(() => {
    if (!open || !session) { setCacheStatus(null); return }
    const token = getAuthToken()
    fetch(`${API_BASE}/playback/session/${session.session_id}/cache-status?token=${encodeURIComponent(token || '')}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => setCacheStatus(d))
      .catch(() => setCacheStatus(null))
  }, [open, session])

  useEffect(() => {
    if (!open) {
      setPhase('idle')
      setError('')
      setReceivedBytes(0)
      setElapsed(0)
      setCacheStatus(null)
    }
  }, [open])

  useEffect(() => {
    if (phase === 'connecting' || phase === 'downloading') {
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [phase])

  if (!open) return null

  const clipDuration = startTime && endTime
    ? Math.max(0, (new Date(endTime).getTime() - new Date(startTime).getTime()) / 1000)
    : 0

  const durationStr = clipDuration > 0 ? formatDuration(clipDuration) : '—'

  // File is instantly available if ACTi prefetched it OR a previous Hikvision
  // stream ran to completion and wrote the dual-output file.
  const fileReady    = session?.is_prefetched === true || cacheStatus?.file_complete === true
  const isRealtime   = !fileReady
  const estimated    = isRealtime ? clipDuration : null   // null → indeterminate / instant
  const progressPct  = estimated ? Math.min(100, (elapsed / estimated) * 100) : null
  const remaining    = estimated ? Math.max(0, estimated - elapsed) : null

  const downloading  = phase === 'connecting' || phase === 'downloading'

  const handleDownload = async () => {
    setPhase('connecting')
    setError('')
    setReceivedBytes(0)
    setElapsed(0)

    try {
      const token = getAuthToken()

      const useSessionFile = fileReady && !!session

      const res = useSessionFile
        ? await fetch(`${window.location.origin}${session.stream_url}`, {
            headers: { Authorization: `Bearer ${token}` },
          })
        : await fetch(`${API_BASE}/playback/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({
              device_id: deviceId,
              channel,
              start_time: startTime instanceof Date ? startTime.toISOString() : startTime,
              end_time:   endTime   instanceof Date ? endTime.toISOString()   : endTime,
            }),
          })

      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try { const j = await res.json(); msg = j.detail || j.message || msg } catch {
          const t = await res.text().catch(() => ''); if (t) msg = t
        }
        throw new Error(msg)
      }

      setPhase('downloading')

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

      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="?([^"]+)"?/)
      const filename = match ? match[1] : `recording_ch${channel}.mp4`

      const blob = new Blob(chunks, { type: 'video/mp4' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)

      setPhase('done')
      onClose?.()
    } catch (e) {
      setError(e.message || 'Download failed')
      setPhase('idle')
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
          <InfoRow label="Device"    value={deviceName || deviceId} />
          <InfoRow label="Channel"   value={`Channel ${channel}`} />
          <InfoRow label="Start"     value={startTime ? new Date(startTime).toLocaleString() : '—'} />
          <InfoRow label="End"       value={endTime   ? new Date(endTime).toLocaleString()   : '—'} />
          <InfoRow label="Duration"  value={durationStr} />

          {/* ── Progress area ── */}
          {downloading && (
            <div style={styles.progressBox}>

              {/* Phase label */}
              <div style={styles.phaseRow}>
                {phase === 'connecting' ? (
                  <span style={styles.phaseLabel}>Connecting to NVR…</span>
                ) : (
                  <span style={styles.phaseLabel}>
                    {progressPct !== null ? `${Math.round(progressPct)}%` : 'Downloading…'}
                  </span>
                )}
                {remaining !== null && phase === 'downloading' && (
                  <span style={styles.countdown}>{formatCountdown(remaining)}</span>
                )}
              </div>

              {/* Progress bar — deterministic if we have an estimate, shimmer if not */}
              <div style={styles.progressBar}>
                {progressPct !== null ? (
                  <div style={{ ...styles.progressFillSolid, width: `${progressPct}%` }} />
                ) : (
                  <div style={styles.progressFillShimmer} />
                )}
              </div>

              {/* Stats row */}
              <div style={styles.progressStats}>
                <span>{formatBytes(receivedBytes)} received</span>
                <span>{formatDuration(elapsed)} elapsed</span>
              </div>

              {/* Real-time speed note */}
              {isRealtime && estimated && phase === 'downloading' && (
                <div style={styles.speedNote}>
                  NVR streams at real-time speed — {formatDuration(estimated)} clip ≈ {formatDuration(estimated)} transfer
                </div>
              )}
            </div>
          )}

          {/* Pre-download note */}
          {!downloading && !error && (
            <div style={styles.note}>
              {fileReady
                ? `Recording cached on server${cacheStatus?.file_size_mb ? ` (${cacheStatus.file_size_mb} MB)` : ''} — download starts immediately.`
                : clipDuration > 0
                  ? `Real-time stream from NVR — estimated transfer time: ${formatDuration(clipDuration)}.`
                  : 'The server will stream the recording directly from the NVR.'}
            </div>
          )}

          {error && <div style={styles.error}>{error}</div>}
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

const shimmerCss = `
@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}
`
if (typeof document !== 'undefined') {
  const s = document.createElement('style')
  s.textContent = shimmerCss
  document.head.appendChild(s)
}

const styles = {
  backdrop: {
    position: 'fixed', inset: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000,
  },
  dialog: {
    backgroundColor: '#1f2937',
    borderRadius: 12,
    border: '1px solid #374151',
    width: 440,
    maxWidth: '90vw',
    overflow: 'hidden',
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid #374151',
  },
  title:    { color: '#f9fafb', fontSize: '1rem', fontWeight: 700 },
  closeBtn: { background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '1rem' },
  body:     { padding: '16px 20px' },
  progressBox: { marginTop: 14 },
  phaseRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 6,
  },
  phaseLabel: { color: '#d1d5db', fontSize: '0.78rem', fontWeight: 600 },
  countdown:  { color: '#60a5fa', fontSize: '0.78rem', fontWeight: 600 },
  progressBar: {
    width: '100%', height: 7,
    backgroundColor: '#374151',
    borderRadius: 4,
    overflow: 'hidden',
    position: 'relative',
  },
  progressFillSolid: {
    height: '100%',
    backgroundColor: '#3b82f6',
    borderRadius: 4,
    transition: 'width 0.8s linear',
  },
  progressFillShimmer: {
    position: 'absolute', top: 0, left: 0,
    height: '100%', width: '40%',
    backgroundColor: '#3b82f6',
    borderRadius: 4,
    animation: 'shimmer 1.4s ease-in-out infinite',
  },
  progressStats: {
    display: 'flex', justifyContent: 'space-between',
    marginTop: 5, color: '#9ca3af', fontSize: '0.72rem',
  },
  speedNote: {
    marginTop: 8,
    color: '#6b7280', fontSize: '0.7rem',
    fontStyle: 'italic',
  },
  note: {
    marginTop: 12, padding: '8px 12px',
    backgroundColor: '#111827',
    borderRadius: 6,
    color: '#9ca3af', fontSize: '0.75rem',
    border: '1px solid #374151',
  },
  error: {
    marginTop: 8, padding: '8px 12px',
    backgroundColor: '#450a0a',
    borderRadius: 6,
    color: '#fca5a5', fontSize: '0.75rem',
    border: '1px solid #7f1d1d',
  },
  footer: {
    display: 'flex', gap: 8, justifyContent: 'flex-end',
    padding: '12px 20px',
    borderTop: '1px solid #374151',
  },
  cancelBtn: {
    backgroundColor: '#374151', color: '#d1d5db',
    border: 'none', borderRadius: 6,
    padding: '8px 16px', fontSize: '0.875rem', cursor: 'pointer',
  },
  downloadBtn: {
    backgroundColor: '#3b82f6', color: '#fff',
    border: 'none', borderRadius: 6,
    padding: '8px 16px', fontSize: '0.875rem',
    fontWeight: 600, cursor: 'pointer',
  },
}
