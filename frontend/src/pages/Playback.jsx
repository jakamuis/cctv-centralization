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
} from 'lucide-react'
import { discoveryApi, playbackApi, getAuthToken } from '../api'
import PlaybackTimeline from '../components/playback/PlaybackTimeline'
import PlaybackDownloadDialog from '../components/playback/PlaybackDownloadDialog'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function normaliseNvr(nvr) {
  return {
    _raw:   nvr,
    id:     nvr.id,
    name:   nvr.branch_name || nvr.device_name || nvr.code || nvr.id,
    code:   nvr.code,
    ip:     nvr.nvr_ip,
    status: nvr.sync_status === 'synced' ? 'online' : 'offline',
    vendor: nvr.vendor || 'hikvision',
  }
}

function normaliseChannel(ch, nvrOnline = true) {
  return {
    _raw:           ch,
    id:             ch.id,
    name:           ch.channel_name || `Channel ${ch.channel_id}`,
    channel_number: ch.channel_id,
    status:         (nvrOnline && ch.is_enabled) ? 'online' : 'offline',
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

// ─── Native Video Player (prefetched MP4) ────────────────────────────────────
// Used for ACTi SNVR sessions where the recording was pre-downloaded to server.

function NativeVideoPlayer({ streamUrl }) {
  const token = getAuthToken()
  const base = streamUrl.startsWith('http') ? streamUrl : `${window.location.origin}${streamUrl}`
  const fullUrl = `${base}${base.includes('?') ? '&' : '?'}token=${encodeURIComponent(token || '')}`

  return (
    <video
      src={fullUrl}
      controls
      autoPlay
      playsInline
      style={{ display: 'block', width: '100%', height: '100%', objectFit: 'contain', background: '#000' }}
    />
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
  segments, searchError, searchAttempted,
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
              const isActi = nvr.vendor === 'acti_snvr'
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
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-xs font-medium">
                        {nvr.name || nvr.code || `NVR ${nvr.id}`}
                      </span>
                      {isActi && (
                        <span className="flex-shrink-0 text-[9px] font-semibold px-1 py-0.5 rounded bg-amber-500/15 text-amber-400 leading-none">
                          ACTi
                        </span>
                      )}
                    </div>
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

        {/* ACTi SNVR notice — shown after a search returns no recordings for this device */}
        {selectedNvr?.vendor === 'acti_snvr' && searchAttempted && !searchLoading && !hasResults && selectedCamera && (
          <div className="mx-3.5 my-3 px-3 py-2.5 bg-amber-500/10 border border-amber-500/20 rounded text-xs text-amber-400 leading-relaxed flex items-start gap-2">
            <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
            <span>ACTi SNVR — no recording data found at this time. The device may not have local storage or may not record this channel.</span>
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
  selectedCamera,
  selectedDate, startTime, endTime,
  session, sessionLoading, sessionError,
  segments,
  timelineBlocks, timelineWindow,
  searchLoading,
  onCloseSession,
  onSeek,
  currentPlaybackTime,
}) {
  const camName   = selectedCamera?.name || '—'
  const dateLabel = selectedDate ? formatDateShort(selectedDate) : '—'
  const timeLabel = startTime && endTime ? `${startTime} – ${endTime}` : ''

  // Elapsed counter while session is loading — drives the ACTi countdown
  const [loadingElapsed, setLoadingElapsed] = useState(0)
  useEffect(() => {
    if (!sessionLoading) { setLoadingElapsed(0); return }
    const id = setInterval(() => setLoadingElapsed(s => s + 1), 1000)
    return () => clearInterval(id)
  }, [sessionLoading])

  // Clip duration in seconds from the time-range strings ("HH:MM")
  const clipDuration = (() => {
    if (!startTime || !endTime) return 0
    const [sh, sm] = startTime.split(':').map(Number)
    const [eh, em] = endTime.split(':').map(Number)
    return Math.max(0, (eh * 60 + em - sh * 60 - sm) * 60)
  })()

  // Both ACTi and Hikvision now pre-fetch the full clip before showing the player.
  // Show a real countdown based on clip duration (= expected download time at 1× real-time).
  const estimated = clipDuration > 0 ? clipDuration : null
  const remaining = estimated ? Math.max(0, estimated - loadingElapsed) : null

  const fmtTime = (s) => {
    const m = Math.floor(s / 60), sec = Math.floor(s % 60)
    return m > 0 ? `${m}m ${s < 0 ? 0 : sec}s` : `${sec}s`
  }

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
              <NativeVideoPlayer
                key={session.session_id}
                streamUrl={session.stream_url}
              />
            </div>
          ) : sessionLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-6">
              <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Video size={26} className="text-primary animate-pulse" />
              </div>

              <p className="text-xs text-muted-foreground">Downloading recording from device…</p>

              {/* Progress bar */}
              <div className="w-full max-w-xs">
                <div className="flex justify-between text-[10px] text-muted-foreground/70 mb-1">
                  <span>{estimated ? `${Math.min(100, Math.round((loadingElapsed / estimated) * 100))}%` : '…'}</span>
                  <span style={{ color: '#60a5fa', fontWeight: 600 }}>
                    {remaining !== null ? (remaining <= 0 ? 'almost done…' : `~${fmtTime(remaining)} remaining`) : ''}
                  </span>
                </div>
                <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all duration-1000"
                    style={{ width: estimated ? `${Math.min(100, (loadingElapsed / estimated) * 100)}%` : '0%' }}
                  />
                </div>
                <p className="text-[10px] text-muted-foreground/50 mt-2 text-center">
                  {fmtTime(loadingElapsed)} elapsed · clip is {clipDuration > 0 ? fmtTime(clipDuration) : '…'} long
                </p>
              </div>
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
          currentTime={currentPlaybackTime}
          onSeek={onSeek}
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
  const [segments,        setSegments]        = useState([])
  const [timelineBlocks,  setTimelineBlocks]  = useState([])
  const [timelineWindow,  setTimelineWindow]  = useState({ start: null, end: null })
  const [searchLoading,   setSearchLoading]   = useState(false)
  const [searchError,     setSearchError]     = useState('')
  const [searchAttempted, setSearchAttempted] = useState(false)

  // Playback session — separate error so play errors are visible in main area
  const [session,        setSession]        = useState(null)
  const [sessionLoading, setSessionLoading] = useState(false)
  const [sessionError,   setSessionError]   = useState('')

  // Track active session for cleanup on unmount
  const sessionRef = useRef(null)
  useEffect(() => { sessionRef.current = session }, [session])

  // Current playback time cursor (wall-clock, updates every second while session active)
  const [currentPlaybackTime, setCurrentPlaybackTime] = useState(null)
  const sessionStartTimeRef   = useRef(null) // Date of start_time on the session
  const sessionCreatedAtRef   = useRef(null) // performance.now() when session was set

  // Download dialog
  const [downloadOpen, setDownloadOpen] = useState(false)

  // Used to cancel the cache-status polling when user closes/changes session
  const prefetchPollRef = useRef({ cancel: false })

  // Sync session start-time refs so the cursor interval can read them without stale closure
  useEffect(() => {
    if (session) {
      sessionStartTimeRef.current  = new Date(session.start_time)
      sessionCreatedAtRef.current  = performance.now()
    } else {
      sessionStartTimeRef.current  = null
      sessionCreatedAtRef.current  = null
      setCurrentPlaybackTime(null)
    }
  }, [session])

  // Tick every second to advance the timeline cursor
  useEffect(() => {
    const id = setInterval(() => {
      if (!sessionStartTimeRef.current || sessionCreatedAtRef.current === null) return
      const elapsed = performance.now() - sessionCreatedAtRef.current
      setCurrentPlaybackTime(new Date(sessionStartTimeRef.current.getTime() + elapsed))
    }, 1000)
    return () => clearInterval(id)
  }, [])

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
    setSearchAttempted(false)
    setCamerasLoading(true)
    discoveryApi.getChannels(nvr.id)
      .then((data) => {
        const raw = Array.isArray(data) ? data : (data?.channels ?? [])
        const nvrOnline = nvr.status === 'online'
        setCameras(raw.map((ch) => normaliseChannel(ch, nvrOnline)))
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
    setSearchAttempted(false)
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
      setSearchAttempted(true)
    }
  }, [selectedNvr, selectedCamera, selectedDate, startTime, endTime])

  const handlePlay = useCallback(async () => {
    if (!selectedNvr || !selectedCamera || !selectedDate) return

    // Cancel any in-progress poll
    prefetchPollRef.current.cancel = true
    const poll = { cancel: false }
    prefetchPollRef.current = poll

    setSessionLoading(true)
    setSessionError('')
    setSession(null)

    const start = buildDateTime(selectedDate, startTime)
    const end   = buildDateTime(selectedDate, endTime)

    try {
      const data = await playbackApi.createSession(
        selectedNvr.id, selectedCamera.channel_id, start, end
      )

      // ACTi: file already ready on the server (synchronous prefetch in backend)
      if (data.is_prefetched) {
        setSession(data)
        return
      }

      // Hikvision / Uniview: background prefetch is running on the server.
      // Poll cache-status until file_complete = true, then show the seekable player.
      const token = getAuthToken()
      const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
      const maxWaitMs = Math.max(180_000, ((end - start) / 1000) * 2 * 1000)
      const started = Date.now()

      while (!poll.cancel) {
        await new Promise(r => setTimeout(r, 2000))
        if (poll.cancel) return

        try {
          const r = await fetch(
            `${API_BASE}/playback/session/${data.session_id}/cache-status?token=${encodeURIComponent(token || '')}`,
          )
          if (r.ok) {
            const s = await r.json()
            if (s.file_complete) {
              setSession(data)
              return
            }
          }
        } catch { /* network hiccup, keep polling */ }

        if (Date.now() - started > maxWaitMs) {
          throw new Error('Playback preparation timed out — the clip may be too long or the NVR is busy')
        }
      }
    } catch (e) {
      if (poll.cancel) return   // user navigated away — suppress error
      console.error('[Playback] Session creation failed:', e)
      setSessionError(e.message || 'Failed to start playback')
    } finally {
      if (!poll.cancel) setSessionLoading(false)
    }
  }, [selectedNvr, selectedCamera, selectedDate, startTime, endTime])

  const handleCloseSession = useCallback(() => {
    prefetchPollRef.current.cancel = true
    const current = session
    setSession(null)
    setSessionLoading(false)
    setSessionError('')
    if (current?.session_id) {
      playbackApi.deleteSession(current.session_id).catch(() => {})
    }
  }, [session])

  // Seek to a specific wall-clock time by creating a new playback session from that point.
  const handleSeek = useCallback(async (seekDate) => {
    if (!selectedNvr || !selectedCamera || !selectedDate) return
    const end = buildDateTime(selectedDate, endTime)
    if (!end || seekDate >= end) return

    // Close current session before starting a new one
    const current = session
    setSession(null)
    setSessionError('')
    if (current?.session_id) {
      playbackApi.deleteSession(current.session_id).catch(() => {})
    }

    setSessionLoading(true)
    try {
      const data = await playbackApi.createSession(
        selectedNvr.id, selectedCamera.channel_id, seekDate, end
      )
      setSession(data)
    } catch (e) {
      setSessionError(e.message || 'Failed to seek — check backend and go2rtc logs')
    } finally {
      setSessionLoading(false)
    }
  }, [selectedNvr, selectedCamera, selectedDate, endTime, session])

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
        searchAttempted={searchAttempted}
        onPlay={handlePlay}
        sessionLoading={sessionLoading}
        onDownload={() => setDownloadOpen(true)}
      />

      <PlaybackMainArea
        selectedCamera={selectedCamera}
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
        onSeek={handleSeek}
        currentPlaybackTime={currentPlaybackTime}
      />

      <PlaybackDownloadDialog
        open={downloadOpen}
        onClose={() => setDownloadOpen(false)}
        deviceId={selectedNvr?.id}
        channel={selectedCamera?.channel_id}
        startTime={buildDateTime(selectedDate, startTime)}
        endTime={buildDateTime(selectedDate, endTime)}
        deviceName={selectedNvr?.name || selectedNvr?.ip}
        session={session}
      />
    </div>
  )
}
