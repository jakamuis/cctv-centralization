/**
 * PlaybackPlayer.jsx
 *
 * Playback video player that reuses the SAME MSE/WebSocket pipeline as LivePlayer.
 * The only difference is the stream_name — which points to a temporary go2rtc
 * playback stream instead of a live stream.
 *
 * Props:
 *   streamName   {string}   go2rtc stream key (from playback session)
 *   sessionId    {string}   playback session UUID (for heartbeat + cleanup)
 *   onClose      {function} called when user closes the player
 *   title        {string}   display title
 */

import React, { useEffect, useRef, useState, useCallback } from 'react'
import { playbackApi } from '../../api'

const LOG = (...args) => console.log('[PlaybackPlayer]', ...args)
const ERR = (...args) => console.error('[PlaybackPlayer]', ...args)

// Heartbeat interval: send keep-alive every 60 seconds
const HEARTBEAT_INTERVAL_MS = 60_000

// ---------------------------------------------------------------------------
// MSE/WebSocket player hook (same logic as LivePlayer)
// ---------------------------------------------------------------------------

function useMsePlayer(videoRef, streamName, enabled) {
  const wsRef = useRef(null)
  const msRef = useRef(null)
  const sbRef = useRef(null)
  const bufRef = useRef(new Uint8Array(4 * 1024 * 1024)) // 4MB buffer for playback
  const bufLenRef = useRef(0)
  const mountedRef = useRef(true)

  const cleanup = useCallback(() => {
    LOG('MSE cleanup for', streamName)
    if (wsRef.current) {
      try { wsRef.current.close() } catch {}
      wsRef.current = null
    }
    if (msRef.current) {
      try { msRef.current.endOfStream() } catch {}
      msRef.current = null
    }
    sbRef.current = null
    bufLenRef.current = 0
    if (videoRef.current) {
      videoRef.current.src = ''
      videoRef.current.load()
    }
  }, [streamName, videoRef])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      cleanup()
    }
  }, [cleanup])

  const connect = useCallback(() => {
    if (!enabled || !streamName || !videoRef.current) return
    cleanup()

    const video = videoRef.current
    video.muted = false // playback can have audio

    const CODECS = [
      'avc1.640029',
      'avc1.64002A',
      'avc1.640033',
      'hvc1.1.6.L153.B0',
      'mp4a.40.2',
      'mp4a.40.5',
      'opus',
    ]
    const supported = CODECS.filter(c => {
      const type = c.includes('vc1') ? `video/mp4; codecs="${c}"` : `audio/mp4; codecs="${c}"`
      return video.canPlayType(type) !== ''
    }).join(',')

    const ms = new MediaSource()
    msRef.current = ms
    video.src = URL.createObjectURL(ms)

    ms.addEventListener('sourceopen', () => {
      LOG('MediaSource sourceopen for playback stream:', streamName)
      URL.revokeObjectURL(video.src)

      const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${wsProto}//${window.location.host}/go2rtc/api/ws?src=${encodeURIComponent(streamName)}`
      LOG('Connecting WebSocket:', wsUrl)

      const ws = new WebSocket(wsUrl)
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      ws.onopen = () => {
        LOG('WS open — sending mse codec request')
        ws.send(JSON.stringify({ type: 'mse', value: supported }))
      }

      ws.onmessage = (ev) => {
        if (typeof ev.data === 'string') {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'mse') {
            LOG('Creating SourceBuffer:', msg.value)
            try {
              const sb = ms.addSourceBuffer(msg.value)
              sb.mode = 'segments'
              sbRef.current = sb

              sb.addEventListener('updateend', () => {
                if (!sb.updating && bufLenRef.current > 0) {
                  try {
                    sb.appendBuffer(bufRef.current.slice(0, bufLenRef.current))
                    bufLenRef.current = 0
                  } catch (e) { /* ignore */ }
                }
                // For playback, keep a larger buffer (30s) to allow seeking
                if (!sb.updating && sb.buffered && sb.buffered.length) {
                  const end = sb.buffered.end(sb.buffered.length - 1)
                  const start = end - 30
                  const start0 = sb.buffered.start(0)
                  if (start > start0 + 5) {
                    try { sb.remove(start0, start0 + 5) } catch {}
                  }
                }
              })
            } catch (e) {
              ERR('addSourceBuffer failed:', e)
            }
          } else if (msg.type === 'error') {
            ERR('WS server error:', msg.value)
          }
        } else {
          const sb = sbRef.current
          if (!sb) return
          const data = new Uint8Array(ev.data)
          if (sb.updating || bufLenRef.current > 0) {
            bufRef.current.set(data, bufLenRef.current)
            bufLenRef.current += data.byteLength
          } else {
            try {
              sb.appendBuffer(ev.data)
            } catch (e) { /* ignore */ }
          }
        }
      }

      ws.onerror = (e) => ERR('WS error:', e)
      ws.onclose = (e) => {
        LOG('WS closed code=', e.code)
        wsRef.current = null
      }
    }, { once: true })

    video.addEventListener('canplay', () => {
      LOG('video canplay — calling play()')
      video.play().catch(err => ERR('play() rejected:', err.name, err.message))
    }, { once: true })

  }, [streamName, enabled, videoRef, cleanup])

  return { connect, cleanup }
}

// ---------------------------------------------------------------------------
// PlaybackPlayer component
// ---------------------------------------------------------------------------

export default function PlaybackPlayer({ streamName, sessionId, onClose, title }) {
  const videoRef = useRef(null)
  const heartbeatRef = useRef(null)
  const mountedRef = useRef(true)

  const [status, setStatus] = useState('connecting') // connecting | playing | error | ended
  const [error, setError] = useState('')
  const [isFullscreen, setIsFullscreen] = useState(false)

  const { connect, cleanup } = useMsePlayer(videoRef, streamName, !!streamName)

  // Start heartbeat to keep session alive
  const startHeartbeat = useCallback(() => {
    if (!sessionId) return
    heartbeatRef.current = setInterval(async () => {
      try {
        await playbackApi.heartbeat(sessionId)
        LOG('Heartbeat sent for session', sessionId)
      } catch (e) {
        ERR('Heartbeat failed:', e)
      }
    }, HEARTBEAT_INTERVAL_MS)
  }, [sessionId])

  const stopHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
    }
  }, [])

  // Connect player when streamName is available
  useEffect(() => {
    if (!streamName) return
    mountedRef.current = true
    LOG('Connecting playback stream:', streamName)
    connect()
    startHeartbeat()

    const video = videoRef.current
    if (!video) return

    const onPlaying = () => {
      if (mountedRef.current) setStatus('playing')
    }
    const onEnded = () => {
      if (mountedRef.current) setStatus('ended')
    }
    const onError = () => {
      if (mountedRef.current) {
        setStatus('error')
        setError('Video playback error')
      }
    }

    video.addEventListener('playing', onPlaying)
    video.addEventListener('ended', onEnded)
    video.addEventListener('error', onError)

    return () => {
      mountedRef.current = false
      video.removeEventListener('playing', onPlaying)
      video.removeEventListener('ended', onEnded)
      video.removeEventListener('error', onError)
      cleanup()
      stopHeartbeat()
    }
  }, [streamName, connect, cleanup, startHeartbeat, stopHeartbeat])

  // Session cleanup is handled by handleClose (explicit) or TTL expiry (navigation away)

  const handleClose = useCallback(async () => {
    stopHeartbeat()
    cleanup()
    if (sessionId) {
      try {
        await playbackApi.deleteSession(sessionId)
      } catch (e) {
        ERR('Session delete on close failed:', e)
      }
    }
    onClose?.()
  }, [sessionId, cleanup, stopHeartbeat, onClose])

  const handleFullscreen = useCallback(() => {
    const el = videoRef.current?.parentElement
    if (!el) return
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {})
      setIsFullscreen(false)
    } else {
      el.requestFullscreen?.().then(() => setIsFullscreen(true)).catch(() => {})
    }
  }, [])

  return (
    <div className="playback-player" style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.title}>{title || 'Playback'}</span>
        <div style={styles.headerActions}>
          <span style={{
            ...styles.statusBadge,
            backgroundColor: status === 'playing' ? '#22c55e' : status === 'error' ? '#ef4444' : '#f59e0b',
          }}>
            {status === 'playing' ? '▶ Playing' : status === 'connecting' ? '⟳ Connecting' : status === 'ended' ? '■ Ended' : '✕ Error'}
          </span>
          <button style={styles.iconBtn} title="Fullscreen" onClick={handleFullscreen}>⤢</button>
          <button style={styles.iconBtn} title="Close" onClick={handleClose}>✕</button>
        </div>
      </div>

      {/* Video area */}
      <div style={styles.videoWrap}>
        {(status === 'connecting') && (
          <div style={styles.overlay}>
            <div style={styles.spinner} />
            <span style={{ color: '#9ca3af', marginTop: 8 }}>Connecting to playback stream…</span>
          </div>
        )}
        {status === 'error' && (
          <div style={styles.overlay}>
            <span style={{ color: '#ef4444', fontSize: '1.5rem' }}>⚠</span>
            <span style={{ color: '#ef4444', marginTop: 8 }}>{error || 'Playback error'}</span>
          </div>
        )}
        {status === 'ended' && (
          <div style={styles.overlay}>
            <span style={{ color: '#9ca3af', fontSize: '1.5rem' }}>■</span>
            <span style={{ color: '#9ca3af', marginTop: 8 }}>Playback ended</span>
          </div>
        )}
        <video
          ref={videoRef}
          playsInline
          autoPlay
          controls
          style={styles.video}
        />
      </div>
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#111827',
    borderRadius: 8,
    overflow: 'hidden',
    border: '1px solid #374151',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    backgroundColor: '#1f2937',
    borderBottom: '1px solid #374151',
  },
  title: {
    color: '#f9fafb',
    fontSize: '0.875rem',
    fontWeight: 600,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: 300,
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  statusBadge: {
    fontSize: '0.7rem',
    padding: '2px 8px',
    borderRadius: 12,
    color: '#fff',
    fontWeight: 600,
  },
  iconBtn: {
    background: 'none',
    border: 'none',
    color: '#9ca3af',
    cursor: 'pointer',
    fontSize: '1rem',
    padding: '2px 6px',
    borderRadius: 4,
    transition: 'color 0.15s',
  },
  videoWrap: {
    position: 'relative',
    backgroundColor: '#000',
    aspectRatio: '16/9',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  overlay: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
    zIndex: 2,
  },
  spinner: {
    width: 32,
    height: 32,
    border: '3px solid #374151',
    borderTopColor: '#3b82f6',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  video: {
    display: 'block',
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  },
}
