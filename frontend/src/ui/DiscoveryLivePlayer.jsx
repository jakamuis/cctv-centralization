import React, { useEffect, useRef, useCallback } from 'react'

/**
 * DiscoveryLivePlayer
 *
 * Minimal MSE-over-WebSocket player for go2rtc.
 * Unlike LivePlayer, this component takes a stream_name directly —
 * no backend startLive call needed. The stream is already registered
 * with go2rtc by the discovery stream endpoint before this mounts.
 *
 * Props:
 *   streamName  {string}  go2rtc stream key (e.g. "site01_1")
 *   title       {string}  display title
 */
export default function DiscoveryLivePlayer({ streamName, title }) {
  const videoRef = useRef(null)
  const wsRef    = useRef(null)
  const msRef    = useRef(null)
  const sbRef    = useRef(null)
  const bufRef   = useRef(new Uint8Array(2 * 1024 * 1024))
  const bufLen   = useRef(0)

  const cleanup = useCallback(() => {
    if (wsRef.current) { try { wsRef.current.close() } catch {} wsRef.current = null }
    if (msRef.current) { try { msRef.current.endOfStream() } catch {} msRef.current = null }
    sbRef.current = null
    bufLen.current = 0
    if (videoRef.current) { videoRef.current.src = ''; videoRef.current.load() }
  }, [])

  useEffect(() => {
    if (!streamName || !videoRef.current) return
    cleanup()

    const video = videoRef.current
    video.muted = true

    const CODECS = [
      'avc1.640029', 'avc1.64002A', 'avc1.640033',
      'hvc1.1.6.L153.B0',
      'mp4a.40.2', 'mp4a.40.5', 'opus',
    ]
    const supported = CODECS.filter(c => {
      const type = c.includes('vc1') ? `video/mp4; codecs="${c}"` : `audio/mp4; codecs="${c}"`
      return video.canPlayType(type) !== ''
    }).join(',')

    const ms = new MediaSource()
    msRef.current = ms
    video.src = URL.createObjectURL(ms)

    ms.addEventListener('sourceopen', () => {
      URL.revokeObjectURL(video.src)

      // Connect via nginx proxy at /go2rtc/ — no hardcoded host
      const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${wsProto}//${window.location.host}/go2rtc/api/ws?src=${encodeURIComponent(streamName)}`
      const ws = new WebSocket(wsUrl)
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      ws.onopen = () => ws.send(JSON.stringify({ type: 'mse', value: supported }))

      ws.onmessage = (ev) => {
        if (typeof ev.data === 'string') {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'mse') {
            try {
              const sb = ms.addSourceBuffer(msg.value)
              sb.mode = 'segments'
              sbRef.current = sb
              sb.addEventListener('updateend', () => {
                if (!sb.updating && bufLen.current > 0) {
                  try { sb.appendBuffer(bufRef.current.slice(0, bufLen.current)); bufLen.current = 0 } catch {}
                }
                if (!sb.updating && sb.buffered && sb.buffered.length) {
                  const end = sb.buffered.end(sb.buffered.length - 1)
                  const start = end - 5
                  const start0 = sb.buffered.start(0)
                  if (start > start0) { try { sb.remove(start0, start) } catch {} }
                  if (video.currentTime < start) video.currentTime = start
                }
              })
            } catch {}
          }
        } else {
          const sb = sbRef.current
          if (!sb) return
          const data = new Uint8Array(ev.data)
          if (sb.updating || bufLen.current > 0) {
            bufRef.current.set(data, bufLen.current)
            bufLen.current += data.byteLength
          } else {
            try { sb.appendBuffer(ev.data) } catch {}
          }
        }
      }

      ws.onerror = () => {}
      ws.onclose = () => { wsRef.current = null }
    }, { once: true })

    video.addEventListener('canplay', () => {
      video.muted = true
      video.play().catch(() => {})
    }, { once: true })

    return cleanup
  }, [streamName, cleanup])

  const onFullscreen = () => {
    const el = videoRef.current?.parentElement
    if (!el) return
    document.fullscreenElement ? document.exitFullscreen().catch(() => {}) : el.requestFullscreen?.().catch(() => {})
  }

  return (
    <div className="live-player connecting">
      <div className="live-header">
        <div className="title">{title || streamName}</div>
        <div className="spacer" />
        <button className="icon" title="Fullscreen" onClick={onFullscreen}>⤢</button>
      </div>
      <div className="video-wrap">
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
