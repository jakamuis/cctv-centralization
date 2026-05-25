/**
 * Playback.jsx — Phase 9 Playback Page
 *
 * Full playback workflow:
 *   1. Select NVR + channel + date
 *   2. Search recordings → show timeline
 *   3. Click Play → create session → stream via same MSE pipeline as live view
 *   4. Download clip via backend proxy
 *
 * Architecture:
 *   - Backend controls ALL session lifecycle
 *   - Frontend never sees camera credentials
 *   - Reuses same WebSocket/MSE player as LivePlayer
 */

import React, { useState, useEffect, useCallback } from 'react'
import { discoveryApi, playbackApi } from '../api'
import RecordingCalendar from '../components/playback/RecordingCalendar'
import PlaybackControls from '../components/playback/PlaybackControls'
import PlaybackTimeline from '../components/playback/PlaybackTimeline'
import PlaybackPlayer from '../components/playback/PlaybackPlayer'
import PlaybackDownloadDialog from '../components/playback/PlaybackDownloadDialog'

const LOG = (...args) => console.log('[Playback]', ...args)
const ERR = (...args) => console.error('[Playback]', ...args)

const TZ_OFFSET = { WIB: 7, WITA: 8, WIT: 9 }

// Build a UTC Date from a local date + time string (HH:MM) in the NVR's timezone.
function buildDateTime(date, timeStr, tzOffset = 7) {
  if (!date || !timeStr) return null
  const [h, m] = timeStr.split(':').map(Number)
  const d = new Date(date)
  // Date.UTC handles negative hours correctly (wraps to previous day).
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), h - tzOffset, m, 0, 0))
}

export default function Playback() {
  // Device selection
  const [nvrs, setNvrs] = useState([])
  const [selectedNvr, setSelectedNvr] = useState(null)
  const [channel, setChannel] = useState(1)

  // Date/time selection
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [startTimeStr, setStartTimeStr] = useState('00:00')
  const [endTimeStr, setEndTimeStr] = useState('23:59')

  // Search results
  const [segments, setSegments] = useState([])
  const [timelineBlocks, setTimelineBlocks] = useState([])
  const [timelineWindow, setTimelineWindow] = useState({ start: null, end: null })
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')

  // Active playback session
  const [session, setSession] = useState(null) // { session_id, stream_name, ... }
  const [sessionLoading, setSessionLoading] = useState(false)
  const [sessionError, setSessionError] = useState('')

  // Download dialog
  const [downloadOpen, setDownloadOpen] = useState(false)

  // Load NVR list on mount
  useEffect(() => {
    discoveryApi.getNvrs()
      .then(data => setNvrs(data.nvrs || data || []))
      .catch(e => ERR('Failed to load NVRs:', e))
  }, [])

  const tzOffset = TZ_OFFSET[selectedNvr?.timezone] ?? 7

  // Search recordings
  const handleSearch = useCallback(async () => {
    if (!selectedNvr || !selectedDate) return
    setSearchLoading(true)
    setSearchError('')
    setSegments([])
    setTimelineBlocks([])
    setSession(null)

    const start = buildDateTime(selectedDate, startTimeStr, tzOffset)
    const end = buildDateTime(selectedDate, endTimeStr, tzOffset)
    if (!start || !end || end <= start) {
      setSearchError('Invalid time range')
      setSearchLoading(false)
      return
    }

    setTimelineWindow({ start, end })

    try {
      // Fetch both search results and timeline in parallel
      const [searchResult, timelineResult] = await Promise.all([
        playbackApi.searchRecordings(selectedNvr.id, channel, start, end),
        playbackApi.getTimeline(selectedNvr.id, channel, start, end),
      ])

      setSegments(searchResult.segments || [])
      setTimelineBlocks(timelineResult.blocks || [])
      LOG('Search complete:', searchResult.total_segments, 'segments')
    } catch (e) {
      ERR('Search failed:', e)
      setSearchError(e.message || 'Search failed')
    } finally {
      setSearchLoading(false)
    }
  }, [selectedNvr, selectedDate, channel, startTimeStr, endTimeStr])

  // Create playback session and start streaming
  const handlePlay = useCallback(async () => {
    if (!selectedNvr || !selectedDate) return
    setSessionLoading(true)
    setSessionError('')

    const start = buildDateTime(selectedDate, startTimeStr, tzOffset)
    const end = buildDateTime(selectedDate, endTimeStr, tzOffset)

    try {
      const data = await playbackApi.createSession(
        selectedNvr.id, channel, start, end
      )
      LOG('Playback session created:', data.session_id, 'stream:', data.stream_name)
      setSession(data)
    } catch (e) {
      ERR('Session creation failed:', e)
      setSessionError(e.message || 'Failed to start playback')
    } finally {
      setSessionLoading(false)
    }
  }, [selectedNvr, selectedDate, channel, startTimeStr, endTimeStr])

  // Close active session
  const handleCloseSession = useCallback(() => {
    setSession(null)
    setSessionError('')
  }, [])

  const hasResults = segments.length > 0

  const playbackTitle = selectedNvr
    ? `${selectedNvr.device_name || selectedNvr.nvr_ip} — Ch${channel} — ${
        selectedDate?.toLocaleDateString()
      } ${startTimeStr}–${endTimeStr}`
    : 'Playback'

  return (
    <div style={styles.page}>
      <div style={styles.pageHeader}>
        <h1 style={styles.pageTitle}>📼 Playback</h1>
        <p style={styles.pageSubtitle}>
          Search and replay recorded footage from Hikvision NVRs
        </p>
      </div>

      <div style={styles.layout}>
        {/* Left sidebar: calendar + controls */}
        <div style={styles.sidebar}>
          <RecordingCalendar
            selectedDate={selectedDate}
            onChange={setSelectedDate}
          />

          <div style={{ marginTop: 12 }}>
            <PlaybackControls
              nvrs={nvrs}
              selectedNvr={selectedNvr}
              onNvrChange={setSelectedNvr}
              channel={channel}
              onChannelChange={setChannel}
              startTime={startTimeStr}
              endTime={endTimeStr}
              onStartTimeChange={setStartTimeStr}
              onEndTimeChange={setEndTimeStr}
              onSearch={handleSearch}
              onPlay={handlePlay}
              loading={searchLoading || sessionLoading}
              hasResults={hasResults}
              timezone={selectedNvr?.timezone || 'WIB'}
            />
          </div>

          {/* Search results summary */}
          {!searchLoading && segments.length > 0 && (
            <div style={styles.resultsSummary}>
              <span style={{ color: '#22c55e', fontWeight: 700 }}>
                ✓ {segments.length} recording segment{segments.length !== 1 ? 's' : ''} found
              </span>
              <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  style={styles.actionBtn}
                  onClick={handlePlay}
                  disabled={sessionLoading}
                >
                  {sessionLoading ? '⟳ Starting…' : '▶ Play Recording'}
                </button>
                <button
                  style={{ ...styles.actionBtn, backgroundColor: '#374151' }}
                  onClick={() => setDownloadOpen(true)}
                >
                  ⬇ Download
                </button>
              </div>
            </div>
          )}

          {!searchLoading && segments.length === 0 && searchError === '' && timelineBlocks.length > 0 && (
            <div style={styles.noResults}>
              No recordings found for the selected time range.
            </div>
          )}

          {searchError && (
            <div style={styles.errorBox}>{searchError}</div>
          )}

          {sessionError && (
            <div style={styles.errorBox}>{sessionError}</div>
          )}
        </div>

        {/* Main content: player + timeline */}
        <div style={styles.main}>
          {/* Active playback session */}
          {session ? (
            <PlaybackPlayer
              streamName={session.stream_name}
              sessionId={session.session_id}
              title={playbackTitle}
              onClose={handleCloseSession}
            />
          ) : (
            <div style={styles.emptyPlayer}>
              <div style={styles.emptyIcon}>📼</div>
              <div style={styles.emptyText}>
                {searchLoading
                  ? 'Searching recordings…'
                  : sessionLoading
                  ? 'Starting playback…'
                  : hasResults
                  ? 'Click ▶ Play to start playback'
                  : 'Select a device, channel, and date, then click Search'}
              </div>
            </div>
          )}

          {/* Timeline */}
          <div style={styles.timelineSection}>
            <div style={styles.timelineHeader}>
              <span style={styles.timelineTitle}>Timeline</span>
              {timelineWindow.start && (
                <span style={styles.timelineDate}>
                  {new Date(timelineWindow.start).toLocaleDateString(undefined, {
                    weekday: 'short', month: 'short', day: 'numeric',
                  })}
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

          {/* Segments list */}
          {segments.length > 0 && (
            <div style={styles.segmentsList}>
              <div style={styles.segmentsHeader}>
                Recording Segments ({segments.length})
              </div>
              <div style={styles.segmentsScroll}>
                {segments.map((seg, i) => (
                  <div key={i} style={styles.segmentRow}>
                    <span style={styles.segmentType}>
                      {seg.recording_type === 'motion' ? '🟣' :
                       seg.recording_type === 'alarm' ? '🔴' : '🔵'}
                      {seg.recording_type || 'normal'}
                    </span>
                    <span style={styles.segmentTime}>
                      {new Date(seg.start).toLocaleTimeString()} –{' '}
                      {new Date(seg.end).toLocaleTimeString()}
                    </span>
                    <span style={styles.segmentDuration}>
                      {Math.round(seg.duration_seconds / 60)}m
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Download dialog */}
      <PlaybackDownloadDialog
        open={downloadOpen}
        onClose={() => setDownloadOpen(false)}
        deviceId={selectedNvr?.id}
        channel={channel}
        startTime={buildDateTime(selectedDate, startTimeStr, tzOffset)}
        endTime={buildDateTime(selectedDate, endTimeStr, tzOffset)}
        deviceName={selectedNvr?.device_name || selectedNvr?.nvr_ip}
      />
    </div>
  )
}

const styles = {
  page: {
    padding: '24px',
    minHeight: '100vh',
    backgroundColor: '#111827',
    color: '#f9fafb',
  },
  pageHeader: {
    marginBottom: 24,
  },
  pageTitle: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: '#f9fafb',
    margin: 0,
  },
  pageSubtitle: {
    color: '#6b7280',
    fontSize: '0.875rem',
    margin: '4px 0 0',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '300px 1fr',
    gap: 20,
    alignItems: 'start',
  },
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  main: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  emptyPlayer: {
    aspectRatio: '16/9',
    backgroundColor: '#1f2937',
    borderRadius: 8,
    border: '2px dashed #374151',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  emptyIcon: {
    fontSize: '3rem',
    opacity: 0.4,
  },
  emptyText: {
    color: '#6b7280',
    fontSize: '0.875rem',
    textAlign: 'center',
    maxWidth: 300,
  },
  timelineSection: {
    backgroundColor: '#1f2937',
    borderRadius: 8,
    padding: '12px 16px',
    border: '1px solid #374151',
  },
  timelineHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  timelineTitle: {
    color: '#f9fafb',
    fontSize: '0.875rem',
    fontWeight: 600,
  },
  timelineDate: {
    color: '#6b7280',
    fontSize: '0.75rem',
  },
  resultsSummary: {
    backgroundColor: '#052e16',
    border: '1px solid #166534',
    borderRadius: 8,
    padding: '12px 16px',
  },
  noResults: {
    backgroundColor: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 8,
    padding: '12px 16px',
    color: '#9ca3af',
    fontSize: '0.875rem',
    textAlign: 'center',
  },
  errorBox: {
    backgroundColor: '#450a0a',
    border: '1px solid #7f1d1d',
    borderRadius: 8,
    padding: '12px 16px',
    color: '#fca5a5',
    fontSize: '0.875rem',
  },
  actionBtn: {
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '6px 14px',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  segmentsList: {
    backgroundColor: '#1f2937',
    borderRadius: 8,
    border: '1px solid #374151',
    overflow: 'hidden',
  },
  segmentsHeader: {
    padding: '10px 16px',
    borderBottom: '1px solid #374151',
    color: '#f9fafb',
    fontSize: '0.875rem',
    fontWeight: 600,
  },
  segmentsScroll: {
    maxHeight: 200,
    overflowY: 'auto',
  },
  segmentRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 16px',
    borderBottom: '1px solid #111827',
    fontSize: '0.8rem',
  },
  segmentType: {
    color: '#9ca3af',
    minWidth: 80,
    textTransform: 'capitalize',
  },
  segmentTime: {
    color: '#d1d5db',
    flex: 1,
    fontFamily: 'monospace',
  },
  segmentDuration: {
    color: '#6b7280',
    minWidth: 40,
    textAlign: 'right',
  },
}
