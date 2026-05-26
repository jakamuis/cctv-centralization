/**
 * Playback.jsx — PlaybackView
 *
 * Layout mirrors the Monitoring page:
 *   Left pane  → NVR list → camera/channel list → date/time + search + results
 *   Main area  → player (MSE) + timeline bar + segments list
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Play,
  Search,
  Calendar,
  Clock,
  Camera,
  Monitor,
  Download,
  X,
  Activity,
  CircleDot,
  Video,
  FileVideo,
  AlertCircle,
  WifiOff,
} from 'lucide-react'
import { discoveryApi, playbackApi } from '../api'
import PlaybackTimeline from '../components/playback/PlaybackTimeline'
import PlaybackDownloadDialog from '../components/playback/PlaybackDownloadDialog'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function normaliseNvr(nvr) {
  return {
    _raw:   nvr,
    id:     nvr.id,
    name:   nvr.branch_name || nvr.device_name || nvr.site_code || nvr.id,
    code:   nvr.site_code,
    ip:     nvr.nvr_ip,
    status: nvr.sync_status === 'synced' ? 'online' : 'offline',
  }
}

function normaliseChannel(ch) {
  return {
    _raw:           ch,
    id:             ch.id,
    name:           ch.channel_name || `Channel ${ch.channel_id}`,
    channel_number: ch.channel_id,
    status:         ch.is_enabled ? 'online' : 'offline',
    channel_id:     ch.channel_id,
  }
}

function buildDateTime(date, timeStr) {
  if (!date || !timeStr) return null
  const [h, m] = timeStr.split(':').map(Number)
  const dt = new Date(date)
  dt.setHours(h, m, 0, 0)
  return dt
}

function toDateInputValue(d) {
  if (!d) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function formatDateShort(d) {
  if (!d) return '—'
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

// ─── Status dots / badges ─────────────────────────────────────────────────────

function StatusDot({ status }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
        status === 'online' ? 'bg-emerald-400' : 'bg-red-500'
      }`}
    />
  )
}

function StatusBadge({ status }) {
  return (
    <span
      className={`text-[11px] font-medium px-2 py-0.5 rounded ${
        status === 'online'
          ? 'bg-emerald-500/15 text-emerald-400'
          : 'bg-red-500/15 text-red-400'
      }`}
    >
      {status === 'online' ? 'Online' : 'Offline'}
    </span>
  )
}

// ─── MSE Playback Player ──────────────────────────────────────────────────────
// Handles: WebSocket/MSE connection, heartbeat, 15 s connection timeout,
//          and video status overlay (connecting / playing / error).
// Session deletion is the caller's (PlaybackView's) responsibility.

function MsePlaybackPlayer({ streamName, sessionId }) {
  const videoRef   = useRef(null)
  const wsRef      = useRef(null)
  const msRef      = useRef(null)
  const sbRef      = useRef(null)
  const bufRef     = useRef(new Uint8Array(4 * 1024 * 1024))
  const bufLen     = useRef(0)
  const timeoutRef = useRef(null)

  const [videoStatus, setVideoStatus] = useState('connecting')

  // ── Heartbeat: keep session alive every 60 s ────────────────────────────────
  useEffect(() => {
    if (!sessionId) return
    const id = setInterval(() => {
      playbackApi.heartbeat(sessionId).catch(() => {})
    }, 60_000)
    return () => clearInterval(id)
  }, [sessionId])

  // ── MSE / WebSocket connection ───────────────────────────────────────────────
  useEffect(() => {
    if (!streamName || !videoRef.current) return

    // Reset state for new stream
    setVideoStatus('connecting')
    clearTimeout(timeoutRef.current)

    if (wsRef.current)  { try { wsRef.current.close()      } catch {} wsRef.current = null }
    if (msRef.current)  { try { msRef.current.endOfStream() } catch {} msRef.current = null }
    sbRef.current = null
    bufLen.current = 0
    if (videoRef.current) { videoRef.current.src = ''; videoRef.current.load() }

    const video = videoRef.current
    video.muted = false

    const CODECS = [
      'avc1.640029', 'avc1.64002A', 'avc1.640033',
      'hvc1.1.6.L153.B0', 'mp4a.40.2', 'mp4a.40.5', 'opus',
    ]
    const supported = CODECS.filter((c) => {
      const type = c.includes('vc1') ? `video/mp4; codecs="${c}"` : `audio/mp4; codecs="${c}"`
      return video.canPlayType(type) !== ''
    }).join(',')

    const ms = new MediaSource()
    msRef.current = ms
    video.src = URL.createObjectURL(ms)

    ms.addEventListener('sourceopen', () => {
      URL.revokeObjectURL(video.src)
      const wsProto    = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const go2rtcHost = window.location.hostname === 'localhost'
        ? 'localhost:1984'
        : `${window.location.hostname}:1984`
      const wsUrl = `${wsProto}//${go2rtcHost}/api/ws?src=${encodeURIComponent(streamName)}`
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
                if (!sb.updating && sb.buffered?.length) {
                  const end = sb.buffered.end(sb.buffered.length - 1)
                  const s0  = sb.buffered.start(0)
                  if (end - 30 > s0 + 5) { try { sb.remove(s0, s0 + 5) } catch {} }
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
      ws.onclose = () => {
        wsRef.current = null
        // If WebSocket closes before video started playing, mark as error
        setVideoStatus((v) => (v === 'connecting' ? 'error' : v))
      }
    }, { once: true })

    // Video playing → clear timeout and mark as playing
    const onPlaying = () => {
      clearTimeout(timeoutRef.current)
      setVideoStatus('playing')
    }
    const onError = () => setVideoStatus('error')
    video.addEventListener('playing', onPlaying, { once: true })
    video.addEventListener('error',   onError)

    video.addEventListener('canplay', () => {
      video.play().catch(() => {})
    }, { once: true })

    // 15-second connection timeout
    timeoutRef.current = setTimeout(() => {
      setVideoStatus((v) => (v === 'connecting' ? 'error' : v))
    }, 15_000)

    return () => {
      clearTimeout(timeoutRef.current)
      video.removeEventListener('playing', onPlaying)
      video.removeEventListener('error',   onError)
      if (wsRef.current)  { try { wsRef.current.close()      } catch {} wsRef.current = null }
      if (msRef.current)  { try { msRef.current.endOfStream() } catch {} msRef.current = null }
      sbRef.current = null
      bufLen.current = 0
      if (videoRef.current) { videoRef.current.src = ''; videoRef.current.load() }
    }
  }, [streamName])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Connecting overlay */}
      {videoStatus === 'connecting' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 z-10 gap-3">
          <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-muted-foreground">Connecting to playback stream…</p>
        </div>
      )}
      {/* Error overlay */}
      {videoStatus === 'error' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 z-10 gap-3">
          <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <WifiOff size={22} className="text-red-400" />
          </div>
          <div className="text-center">
            <p className="text-xs text-red-400 font-medium">Playback stream unavailable</p>
            <p className="text-[10px] text-muted-foreground mt-1">Check NVR connectivity · go2rtc logs</p>
          </div>
        </div>
      )}
      <video
        ref={videoRef}
        playsInline
        autoPlay
        controls
        style={{ display: 'block', width: '100%', height: '100%', objectFit: 'contain', background: '#000' }}
      />
    </div>
  )
}

// ─── Left Pane ────────────────────────────────────────────────────────────────

function PlaybackLeftPane({
  nvrs, nvrsLoading,
  selectedNvr, onSelectNvr,
  cameras, camerasLoading,
  selectedCamera, onSelectCamera,
  selectedDate, onDateChange,
  startTime, onStartTimeChange,
  endTime,   onEndTimeChange,
  onSearch, searchLoading,
  segments, searchError,
  onPlay, sessionLoading,
  onDownload,
}) {
  const [nvrSearch,    setNvrSearch]    = useState('')
  const [cameraSearch, setCameraSearch] = useState('')

  const filteredNvrs = nvrs.filter((n) =>
    nvrSearch === '' ||
    (n.name || n.code || '').toLowerCase().includes(nvrSearch.toLowerCase())
  )

  const filteredCameras = cameras.filter((c) =>
    cameraSearch === '' ||
    (c.name || '').toLowerCase().includes(cameraSearch.toLowerCase())
  )

  const hasResults  = segments.length > 0
  const canSearch   = !!selectedNvr && !!selectedCamera && !!selectedDate
  const isSearching = searchLoading || sessionLoading

  return (
    <aside className="w-72 flex flex-col border-r border-border bg-card flex-shrink-0 overflow-hidden">

      {/* ── Header ── */}
      <div className="flex items-center gap-2 px-3.5 py-3 border-b border-border flex-shrink-0">
        <div className="w-6 h-6 rounded bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
          <Play size={12} className="text-primary" />
        </div>
        <span className="text-sm font-semibold text-foreground">Playback</span>
      </div>

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto">

        {/* Device (NVR) section */}
        <div className="border-b border-border">
          <div className="flex items-center justify-between px-3.5 py-2.5">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Device</p>
            <span className="text-[10px] text-muted-foreground">{nvrs.length} NVRs</span>
          </div>
          <div className="px-3.5 pb-2">
            <div className="flex items-center gap-2 bg-[#1a2436] border border-border rounded px-2.5 py-1.5">
              <Search size={11} className="text-muted-foreground flex-shrink-0" />
              <input
                type="text"
                value={nvrSearch}
                onChange={(e) => setNvrSearch(e.target.value)}
                placeholder="Search NVRs…"
                className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
              />
            </div>
          </div>
          <div className="max-h-36 overflow-y-auto">
            {nvrsLoading && (
              <div className="px-4 py-3 text-muted-foreground text-xs">Loading…</div>
            )}
            {!nvrsLoading && filteredNvrs.length === 0 && (
              <div className="px-4 py-3 text-muted-foreground text-xs">
                {nvrSearch ? 'No matches' : 'No devices found'}
              </div>
            )}
            {!nvrsLoading && filteredNvrs.map((nvr) => {
              const isActive = selectedNvr?.id === nvr.id
              return (
                <button
                  key={nvr.id}
                  onClick={() => onSelectNvr(nvr)}
                  className={`w-full flex items-center gap-2.5 px-3.5 py-2 transition-colors relative ${
                    isActive ? 'bg-accent/40 text-primary' : 'text-foreground hover:bg-secondary/50'
                  }`}
                >
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r" />
                  )}
                  <Monitor size={13} className={`flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                  <div className="flex-1 min-w-0 text-left">
                    <span className="block truncate text-xs font-medium">
                      {nvr.name || nvr.code || `NVR ${nvr.id}`}
                    </span>
                    {nvr.ip && (
                      <span className="block truncate text-[10px] text-muted-foreground leading-tight">{nvr.ip}</span>
                    )}
                  </div>
                  <StatusDot status={nvr.status} />
                </button>
              )
            })}
          </div>
        </div>

        {/* Camera / Channel section */}
        <div className="border-b border-border">
          <div className="flex items-center justify-between px-3.5 py-2.5">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Camera</p>
            {selectedNvr && (
              <span className="text-[10px] text-muted-foreground">{cameras.length} ch</span>
            )}
          </div>
          {!selectedNvr ? (
            <div className="px-4 pb-3 text-muted-foreground text-xs text-center leading-relaxed">
              Select a device first
            </div>
          ) : (
            <>
              <div className="px-3.5 pb-2">
                <div className="flex items-center gap-2 bg-[#1a2436] border border-border rounded px-2.5 py-1.5">
                  <Search size={11} className="text-muted-foreground flex-shrink-0" />
                  <input
                    type="text"
                    value={cameraSearch}
                    onChange={(e) => setCameraSearch(e.target.value)}
                    placeholder="Search cameras…"
                    className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
                  />
                </div>
              </div>
              <div className="max-h-36 overflow-y-auto">
                {camerasLoading && (
                  <div className="px-4 py-3 text-muted-foreground text-xs">Loading…</div>
                )}
                {!camerasLoading && filteredCameras.length === 0 && (
                  <div className="px-4 py-3 text-muted-foreground text-xs">
                    {cameraSearch ? 'No matches' : 'No cameras in this device'}
                  </div>
                )}
                {!camerasLoading && filteredCameras.map((cam) => {
                  const isActive = selectedCamera?.id === cam.id
                  return (
                    <button
                      key={cam.id}
                      onClick={() => onSelectCamera(cam)}
                      className={`w-full flex items-center gap-2.5 px-3.5 py-2 transition-colors relative ${
                        isActive ? 'bg-accent/40 text-primary' : 'text-foreground hover:bg-secondary/50'
                      }`}
                    >
                      {isActive && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r" />
                      )}
                      <Camera size={13} className={`flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                      <div className="flex-1 min-w-0 text-left">
                        <p className="truncate text-xs font-medium leading-tight">{cam.name}</p>
                        {cam.channel_number != null && (
                          <p className="text-[10px] text-muted-foreground leading-tight">Ch {cam.channel_number}</p>
                        )}
                      </div>
                      <StatusDot status={cam.status} />
                    </button>
                  )
                })}
              </div>
            </>
          )}
        </div>

        {/* Date & Time section */}
        <div className="border-b border-border px-3.5 py-3 space-y-3">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Date & Time</p>
          <div className="space-y-1">
            <label className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <Calendar size={10} />
              Date
            </label>
            <input
              type="date"
              value={toDateInputValue(selectedDate)}
              onChange={(e) => onDateChange(e.target.value ? new Date(e.target.value + 'T12:00:00') : new Date())}
              className="w-full bg-[#1a2436] border border-border rounded px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-primary/50 transition-colors"
            />
          </div>
          <div className="flex gap-2">
            <div className="flex-1 space-y-1">
              <label className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <Clock size={10} />
                From
              </label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => onStartTimeChange(e.target.value)}
                className="w-full bg-[#1a2436] border border-border rounded px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-primary/50 transition-colors"
              />
            </div>
            <div className="flex-1 space-y-1">
              <label className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <Clock size={10} />
                To
              </label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => onEndTimeChange(e.target.value)}
                className="w-full bg-[#1a2436] border border-border rounded px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-primary/50 transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Search button */}
        <div className="px-3.5 py-3 border-b border-border">
          <button
            onClick={onSearch}
            disabled={isSearching || !canSearch}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold rounded transition-colors"
          >
            {searchLoading ? (
              <>
                <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                Searching…
              </>
            ) : (
              <>
                <Search size={13} />
                Search Recordings
              </>
            )}
          </button>
          {!canSearch && !searchLoading && (
            <p className="text-[10px] text-muted-foreground text-center mt-1.5">
              Select device, camera, and date
            </p>
          )}
        </div>

        {/* Results summary */}
        {!searchLoading && hasResults && (
          <div className="px-3.5 py-3 border-b border-border space-y-2">
            <div className="flex items-center gap-1.5">
              <CircleDot size={11} className="text-emerald-400" />
              <span className="text-xs font-medium text-emerald-400">
                {segments.length} segment{segments.length !== 1 ? 's' : ''} found
              </span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={onPlay}
                disabled={sessionLoading}
                className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-xs font-medium rounded transition-colors"
              >
                {sessionLoading ? (
                  <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Play size={11} />
                )}
                {sessionLoading ? 'Starting…' : 'Play'}
              </button>
              <button
                onClick={onDownload}
                className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 bg-secondary hover:bg-secondary/80 border border-border text-foreground text-xs font-medium rounded transition-colors"
              >
                <Download size={11} />
                Download
              </button>
            </div>
          </div>
        )}

        {/* Search error */}
        {searchError && (
          <div className="mx-3.5 my-3 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400 leading-relaxed flex items-start gap-2">
            <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
            <span>{searchError}</span>
          </div>
        )}

        {/* Segments list */}
        {segments.length > 0 && (
          <div className="border-b border-border">
            <div className="flex items-center gap-1.5 px-3.5 py-2.5">
              <FileVideo size={11} className="text-muted-foreground" />
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                Segments ({segments.length})
              </p>
            </div>
            <div className="max-h-48 overflow-y-auto">
              {segments.map((seg, i) => {
                const typeColor =
                  seg.recording_type === 'motion' ? 'bg-violet-500' :
                  seg.recording_type === 'alarm'  ? 'bg-red-500' :
                  'bg-blue-500'
                return (
                  <div
                    key={i}
                    className="flex items-center gap-2.5 px-3.5 py-2 border-b border-border/50 last:border-0"
                  >
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${typeColor}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] font-medium text-foreground capitalize truncate">
                        {seg.recording_type || 'normal'}
                      </p>
                      <p className="text-[10px] text-muted-foreground font-mono leading-tight">
                        {new Date(seg.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        {' – '}
                        {new Date(seg.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    <span className="text-[10px] text-muted-foreground flex-shrink-0">
                      {Math.round(seg.duration_seconds / 60)}m
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

// ─── Main Area ────────────────────────────────────────────────────────────────

function PlaybackMainArea({
  selectedCamera, selectedNvr,
  selectedDate, startTime, endTime,
  session, sessionLoading, sessionError,
  segments,
  timelineBlocks, timelineWindow,
  searchLoading,
  onCloseSession,
}) {
  const camName   = selectedCamera?.name || '—'
  const dateLabel = selectedDate ? formatDateShort(selectedDate) : '—'
  const timeLabel = startTime && endTime ? `${startTime} – ${endTime}` : ''

  return (
    <section className="flex-1 flex flex-col bg-background min-w-0 overflow-hidden">

      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-sm font-semibold text-foreground">Recording Player</span>
          {selectedCamera && (
            <>
              <span className="text-muted-foreground">·</span>
              <span className="text-xs text-muted-foreground truncate">{camName}</span>
              <StatusBadge status={selectedCamera.status} />
            </>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 text-xs text-muted-foreground">
          {selectedDate && (
            <span className="flex items-center gap-1.5">
              <Calendar size={12} />
              {dateLabel}
            </span>
          )}
          {timeLabel && (
            <span className="flex items-center gap-1.5">
              <Clock size={12} />
              {timeLabel}
            </span>
          )}
          {session && (
            <button
              onClick={onCloseSession}
              className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-red-400 transition-colors"
              title="Close playback session"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* ── Player area ── */}
      <div className="flex-1 flex flex-col items-center justify-center p-5 bg-[#0a0f18] min-h-0 gap-3">
        <div
          className="relative bg-black rounded-lg border border-border overflow-hidden w-full"
          style={{ maxWidth: '720px', aspectRatio: '16/9' }}
        >
          {session ? (
            <div className="absolute inset-0">
              <MsePlaybackPlayer
                key={session.session_id}
                streamName={session.stream_name}
                sessionId={session.session_id}
              />
            </div>
          ) : sessionLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Video size={26} className="text-primary animate-pulse" />
              </div>
              <p className="text-xs text-muted-foreground">Starting playback stream…</p>
            </div>
          ) : searchLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-muted-foreground">Searching recordings…</p>
            </div>
          ) : !selectedCamera ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="w-14 h-14 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
                <Play size={24} className="text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">No camera selected</p>
                <p className="text-xs text-muted-foreground mt-1">Select a device and camera from the left panel</p>
              </div>
            </div>
          ) : segments.length > 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Play size={24} className="text-primary" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">{camName}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {segments.length} recording{segments.length !== 1 ? 's' : ''} found — click Play in the sidebar
                </p>
              </div>
            </div>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="w-14 h-14 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
                <Camera size={24} className="text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">{camName}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Select a date and time range, then click Search
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Session error — shown prominently below the player */}
        {sessionError && (
          <div
            className="w-full flex items-start gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400"
            style={{ maxWidth: '720px' }}
          >
            <AlertCircle size={13} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Playback session failed</p>
              <p className="text-red-400/80 mt-0.5 leading-relaxed">{sessionError}</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Timeline ── */}
      <div className="flex-shrink-0 border-t border-border bg-card px-4 py-3">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <Activity size={13} className="text-muted-foreground" />
            <span className="text-xs font-semibold text-foreground">Timeline</span>
          </div>
          {timelineWindow.start && (
            <span className="text-[10px] text-muted-foreground">
              {formatDateShort(timelineWindow.start)}
            </span>
          )}
        </div>
        <PlaybackTimeline
          blocks={timelineBlocks}
          windowStart={timelineWindow.start}
          windowEnd={timelineWindow.end}
          loading={searchLoading}
        />
      </div>
    </section>
  )
}

// ─── Root PlaybackView ────────────────────────────────────────────────────────

export default function PlaybackView() {
  // NVR / camera selection
  const [nvrs,           setNvrs]           = useState([])
  const [nvrsLoading,    setNvrsLoading]    = useState(true)
  const [cameras,        setCameras]        = useState([])
  const [camerasLoading, setCamerasLoading] = useState(false)
  const [selectedNvr,    setSelectedNvr]    = useState(null)
  const [selectedCamera, setSelectedCamera] = useState(null)

  // Date / time
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [startTime,    setStartTime]    = useState('00:00')
  const [endTime,      setEndTime]      = useState('23:59')

  // Search
  const [segments,       setSegments]       = useState([])
  const [timelineBlocks, setTimelineBlocks] = useState([])
  const [timelineWindow, setTimelineWindow] = useState({ start: null, end: null })
  const [searchLoading,  setSearchLoading]  = useState(false)
  const [searchError,    setSearchError]    = useState('')

  // Playback session — separate error so play errors are visible in main area
  const [session,        setSession]        = useState(null)
  const [sessionLoading, setSessionLoading] = useState(false)
  const [sessionError,   setSessionError]   = useState('')

  // Track active session for cleanup on unmount
  const sessionRef = useRef(null)
  useEffect(() => { sessionRef.current = session }, [session])

  // Download dialog
  const [downloadOpen, setDownloadOpen] = useState(false)

  // Cleanup active session when user navigates away
  useEffect(() => {
    return () => {
      if (sessionRef.current?.session_id) {
        playbackApi.deleteSession(sessionRef.current.session_id).catch(() => {})
      }
    }
  }, [])

  // Load NVRs on mount
  useEffect(() => {
    setNvrsLoading(true)
    discoveryApi.getNvrs()
      .then((data) => {
        const list = Array.isArray(data) ? data : (data?.nvrs ?? [])
        setNvrs(list.map(normaliseNvr))
      })
      .catch((e) => console.error('[Playback] Failed to load NVRs:', e))
      .finally(() => setNvrsLoading(false))
  }, [])

  const handleSelectNvr = useCallback((nvr) => {
    setSelectedNvr(nvr)
    setSelectedCamera(null)
    setCameras([])
    setSegments([])
    setTimelineBlocks([])
    setSession(null)
    setSearchError('')
    setSessionError('')
    setCamerasLoading(true)
    discoveryApi.getChannels(nvr.id)
      .then((data) => {
        const raw = Array.isArray(data) ? data : (data?.channels ?? [])
        setCameras(raw.map(normaliseChannel))
      })
      .catch((e) => console.error('[Playback] Failed to load channels:', e))
      .finally(() => setCamerasLoading(false))
  }, [])

  const handleSelectCamera = useCallback((cam) => {
    setSelectedCamera(cam)
    setSegments([])
    setTimelineBlocks([])
    setSession(null)
    setSearchError('')
    setSessionError('')
  }, [])

  const handleSearch = useCallback(async () => {
    if (!selectedNvr || !selectedCamera || !selectedDate) return
    setSearchLoading(true)
    setSearchError('')
    setSessionError('')
    setSegments([])
    setTimelineBlocks([])
    setSession(null)

    const start = buildDateTime(selectedDate, startTime)
    const end   = buildDateTime(selectedDate, endTime)
    if (!start || !end || end <= start) {
      setSearchError('Invalid time range — end must be after start')
      setSearchLoading(false)
      return
    }
    setTimelineWindow({ start, end })

    try {
      const [searchResult, timelineResult] = await Promise.all([
        playbackApi.searchRecordings(selectedNvr.id, selectedCamera.channel_id, start, end),
        playbackApi.getTimeline(selectedNvr.id, selectedCamera.channel_id, start, end),
      ])
      setSegments(searchResult.segments || [])
      setTimelineBlocks(timelineResult.blocks || [])
    } catch (e) {
      console.error('[Playback] Search failed:', e)
      setSearchError(e.message || 'Search failed — check connection and try again')
    } finally {
      setSearchLoading(false)
    }
  }, [selectedNvr, selectedCamera, selectedDate, startTime, endTime])

  const handlePlay = useCallback(async () => {
    if (!selectedNvr || !selectedCamera || !selectedDate) return
    setSessionLoading(true)
    setSessionError('')

    const start = buildDateTime(selectedDate, startTime)
    const end   = buildDateTime(selectedDate, endTime)

    try {
      const data = await playbackApi.createSession(
        selectedNvr.id, selectedCamera.channel_id, start, end
      )
      setSession(data)
    } catch (e) {
      console.error('[Playback] Session creation failed:', e)
      // Store in sessionError so it shows prominently in the main area
      setSessionError(e.message || 'Failed to start playback — check backend and go2rtc logs')
    } finally {
      setSessionLoading(false)
    }
  }, [selectedNvr, selectedCamera, selectedDate, startTime, endTime])

  const handleCloseSession = useCallback(() => {
    const current = session
    setSession(null)
    setSessionError('')
    if (current?.session_id) {
      playbackApi.deleteSession(current.session_id).catch(() => {})
    }
  }, [session])

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden">
      <PlaybackLeftPane
        nvrs={nvrs}
        nvrsLoading={nvrsLoading}
        selectedNvr={selectedNvr}
        onSelectNvr={handleSelectNvr}
        cameras={cameras}
        camerasLoading={camerasLoading}
        selectedCamera={selectedCamera}
        onSelectCamera={handleSelectCamera}
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
        startTime={startTime}
        onStartTimeChange={setStartTime}
        endTime={endTime}
        onEndTimeChange={setEndTime}
        onSearch={handleSearch}
        searchLoading={searchLoading}
        segments={segments}
        searchError={searchError}
        onPlay={handlePlay}
        sessionLoading={sessionLoading}
        onDownload={() => setDownloadOpen(true)}
      />

      <PlaybackMainArea
        selectedCamera={selectedCamera}
        selectedNvr={selectedNvr}
        selectedDate={selectedDate}
        startTime={startTime}
        endTime={endTime}
        session={session}
        sessionLoading={sessionLoading}
        sessionError={sessionError}
        segments={segments}
        timelineBlocks={timelineBlocks}
        timelineWindow={timelineWindow}
        searchLoading={searchLoading}
        onCloseSession={handleCloseSession}
      />

      <PlaybackDownloadDialog
        open={downloadOpen}
        onClose={() => setDownloadOpen(false)}
        deviceId={selectedNvr?.id}
        channel={selectedCamera?.channel_id}
        startTime={buildDateTime(selectedDate, startTime)}
        endTime={buildDateTime(selectedDate, endTime)}
        deviceName={selectedNvr?.name || selectedNvr?.ip}
      />
    </div>
  )
}
