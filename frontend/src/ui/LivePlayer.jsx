import React, { useEffect, useRef, useState, useCallback } from 'react'
import { api, getViewerId } from '../api'

const LOG = (...args) => console.log('[LivePlayer]', ...args)
const ERR = (...args) => console.error('[LivePlayer]', ...args)

// go2rtc public base URL — must be reachable from the browser
const GO2RTC_URL = 'http://localhost:1984'

/**
 * MSE-over-WebSocket player for go2rtc.
 *
 * go2rtc serves fMP4 segments over a WebSocket connection.
 * Protocol:
 *   1. Connect to ws://go2rtc/api/ws?src=<stream_name>
 *   2. Client sends: {"type":"mse","value":"<supported codecs>"}
 *   3. Server replies: {"type":"mse","value":"video/mp4; codecs=\"hvc1...,mp4a...\""}
 *   4. Server streams binary fMP4 data → append to MediaSource SourceBuffer
 *
 * This works with H.265 (hvc1) on Chrome/Edge via MSE, unlike hls.js which
 * only supports H.264.
 */
function useMsePlayer(videoRef, streamName, enabled) {
  const wsRef = useRef(null)
  const msRef = useRef(null)
  const sbRef = useRef(null)
  const bufRef = useRef(new Uint8Array(2 * 1024 * 1024))
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
    video.muted = true

    // Build supported codec list (same as go2rtc video-rtc.js)
    const CODECS = [
      'avc1.640029',       // H.264 high 4.1
      'avc1.64002A',       // H.264 high 4.2
      'avc1.640033',       // H.264 high 5.1
      'hvc1.1.6.L153.B0',  // H.265 main 5.1
      'mp4a.40.2',         // AAC LC
      'mp4a.40.5',         // AAC HE
      'opus',              // OPUS
    ]
    const supported = CODECS.filter(c => {
      const type = c.includes('vc1') ? `video/mp4; codecs="${c}"` : `audio/mp4; codecs="${c}"`
      return video.canPlayType(type) !== ''
    }).join(',')
    LOG('Supported codecs:', supported)

    // Create MediaSource
    const ms = new MediaSource()
    msRef.current = ms
    video.src = URL.createObjectURL(ms)

    ms.addEventListener('sourceopen', () => {
      LOG('MediaSource sourceopen')
      URL.revokeObjectURL(video.src)

      // Connect WebSocket
      const wsUrl = `ws://localhost:1984/api/ws?src=${encodeURIComponent(streamName)}`
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
          LOG('WS message:', msg)

          if (msg.type === 'mse') {
            // Server confirmed codec — create SourceBuffer
            LOG('Creating SourceBuffer with mimeType:', msg.value)
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

                // Keep buffer trimmed to last 5s for live
                if (!sb.updating && sb.buffered && sb.buffered.length) {
                  const end = sb.buffered.end(sb.buffered.length - 1)
                  const start = end - 5
                  const start0 = sb.buffered.start(0)
                  if (start > start0) {
                    try { sb.remove(start0, start) } catch {}
                  }
                  if (video.currentTime < start) {
                    video.currentTime = start
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
          // Binary fMP4 data — append to SourceBuffer
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
        LOG('WS closed code=', e.code, 'reason=', e.reason)
        wsRef.current = null
      }
    }, { once: true })

    // Autoplay once data arrives
    video.addEventListener('canplay', () => {
      LOG('video canplay — calling play()')
      video.muted = true
      video.play().catch(err => ERR('play() rejected:', err.name, err.message))
    }, { once: true })

    video.addEventListener('playing', () => LOG('video playing — frames visible'))
    video.addEventListener('stalled', () => LOG('video stalled'))
    video.addEventListener('error', () => ERR('video error:', video.error))

  }, [streamName, enabled, videoRef, cleanup])

  return { connect, cleanup }
}

export default function LivePlayer({ cameraId, title, useSubstream = false, muted = true }) {
  const videoRef = useRef(null)
  const mountedRef = useRef(false)
  const reconnectTimer = useRef(null)

  const [state, setState] = useState({ status: 'idle', error: '', streamName: null })

  // Fetch stream info from backend, then connect MSE player
  const startStream = useCallback(async () => {
    if (!mountedRef.current || !cameraId) return
    LOG('startStream cameraId=', cameraId)
    setState({ status: 'loading', error: '', streamName: null })

    try {
      const data = await api.startLive(cameraId, { viewerId: getViewerId() })
      LOG('startLive response:', data)
      if (!mountedRef.current) return

      const { stream_name } = data
      if (!stream_name) throw new Error('No stream_name in response')

      setState({ status: 'connecting', error: '', streamName: stream_name })
    } catch (e) {
      ERR('startStream error:', e)
      if (!mountedRef.current) return
      setState({ status: 'error', error: e?.message || 'Failed to start stream', streamName: null })
      scheduleReconnect()
    }
  }, [cameraId])

  const scheduleReconnect = useCallback(() => {
    if (!mountedRef.current) return
    if (reconnectTimer.current) return
    LOG('scheduleReconnect in 3s')
    reconnectTimer.current = setTimeout(() => {
      reconnectTimer.current = null
      startStream()
    }, 3000)
  }, [startStream])

  useEffect(() => {
    mountedRef.current = true
    startStream()
    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
      api.stopLive(cameraId).catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraId])

  // MSE player — activates once we have a stream_name
  const { connect, cleanup } = useMsePlayer(videoRef, state.streamName, !!state.streamName)

  useEffect(() => {
    if (!state.streamName) return
    LOG('stream_name ready:', state.streamName, '— connecting MSE player')
    connect()
    setState(s => ({ ...s, status: 'loading' }))

    // Listen for video playing to update status
    const video = videoRef.current
    if (!video) return
    const onPlaying = () => {
      LOG('video playing event — setting status=playing')
      setState(s => ({ ...s, status: 'playing' }))
    }
    video.addEventListener('playing', onPlaying)
    return () => {
      video.removeEventListener('playing', onPlaying)
      cleanup()
    }
  }, [state.streamName, connect, cleanup])

  const onFullscreen = () => {
    const el = videoRef.current?.parentElement
    if (!el) return
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {})
    } else {
      el.requestFullscreen?.().catch(() => {})
    }
  }

  return (
    <div className={`live-player ${state.status}`}>
      <div className="live-header">
        <div className="title">{title || 'Live'}</div>
        <div className="spacer" />
        <button className="icon" title="Fullscreen" onClick={onFullscreen}>⤢</button>
      </div>
      <div className="video-wrap">
        {(state.status === 'loading' || state.status === 'connecting') && (
          <div className="overlay muted">Connecting…</div>
        )}
        {state.status === 'error' && (
          <div className="overlay error">{state.error || 'Offline'}</div>
        )}
        <video
          ref={videoRef}
          muted
          playsInline
          autoPlay
          controls={false}
          style={{ display: 'block', width: '100%', height: '100%', objectFit: 'contain' }}
        />
      </div>
    </div>
  )
}
