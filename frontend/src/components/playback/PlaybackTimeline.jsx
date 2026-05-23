/**
 * PlaybackTimeline.jsx
 *
 * Visual timeline bar showing recording blocks and gaps.
 * Supports click-to-seek and a current time cursor.
 *
 * Props:
 *   blocks        {Array}    timeline blocks from /api/playback/timeline
 *   windowStart   {Date}     start of the timeline window
 *   windowEnd     {Date}     end of the timeline window
 *   currentTime   {Date}     current playback cursor position
 *   onSeek        {function} called with (Date) when user clicks the timeline
 *   loading       {boolean}  show loading state
 */

import React, { useCallback, useRef } from 'react'

const RECORDING_COLOR = '#3b82f6'   // blue
const GAP_COLOR = '#1f2937'         // dark gray
const CURSOR_COLOR = '#f59e0b'      // amber
const MOTION_COLOR = '#8b5cf6'      // purple
const ALARM_COLOR = '#ef4444'       // red

function blockColor(block) {
  if (block.type === 'gap') return GAP_COLOR
  switch (block.recording_type) {
    case 'motion': return MOTION_COLOR
    case 'alarm':  return ALARM_COLOR
    default:       return RECORDING_COLOR
  }
}

export default function PlaybackTimeline({
  blocks = [],
  windowStart,
  windowEnd,
  currentTime,
  onSeek,
  loading = false,
}) {
  const barRef = useRef(null)

  const windowMs = windowEnd && windowStart
    ? new Date(windowEnd).getTime() - new Date(windowStart).getTime()
    : 0

  const toPercent = useCallback((dt) => {
    if (!windowMs || !windowStart) return 0
    const ms = new Date(dt).getTime() - new Date(windowStart).getTime()
    return Math.max(0, Math.min(100, (ms / windowMs) * 100))
  }, [windowMs, windowStart])

  const handleClick = useCallback((e) => {
    if (!onSeek || !windowStart || !windowMs) return
    const rect = barRef.current?.getBoundingClientRect()
    if (!rect) return
    const x = e.clientX - rect.left
    const pct = Math.max(0, Math.min(1, x / rect.width))
    const seekMs = new Date(windowStart).getTime() + pct * windowMs
    onSeek(new Date(seekMs))
  }, [onSeek, windowStart, windowMs])

  const cursorPct = currentTime ? toPercent(currentTime) : null

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingBar}>
          <div style={styles.loadingPulse} />
        </div>
        <div style={styles.labels}>
          <span style={styles.label}>Loading timeline…</span>
        </div>
      </div>
    )
  }

  if (!windowStart || !windowEnd) {
    return (
      <div style={styles.container}>
        <div style={{ ...styles.bar, backgroundColor: GAP_COLOR }} />
        <div style={styles.labels}>
          <span style={styles.label}>Select a date to load timeline</span>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {/* Timeline bar */}
      <div
        ref={barRef}
        style={styles.bar}
        onClick={handleClick}
        title="Click to seek"
      >
        {/* Render blocks */}
        {blocks.map((block, i) => {
          const left = toPercent(block.start)
          const right = toPercent(block.end)
          const width = right - left
          if (width < 0.05) return null
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${left}%`,
                width: `${width}%`,
                top: 0,
                bottom: 0,
                backgroundColor: blockColor(block),
                opacity: block.type === 'gap' ? 0.3 : 0.9,
                transition: 'opacity 0.1s',
              }}
              title={`${block.type === 'recording' ? '🎬' : '⬜'} ${
                new Date(block.start).toLocaleTimeString()
              } – ${new Date(block.end).toLocaleTimeString()} (${
                Math.round(block.duration_seconds / 60)
              }m)`}
            />
          )
        })}

        {/* Current time cursor */}
        {cursorPct !== null && (
          <div
            style={{
              position: 'absolute',
              left: `${cursorPct}%`,
              top: 0,
              bottom: 0,
              width: 2,
              backgroundColor: CURSOR_COLOR,
              zIndex: 10,
              pointerEvents: 'none',
              boxShadow: `0 0 4px ${CURSOR_COLOR}`,
            }}
          />
        )}
      </div>

      {/* Time labels */}
      <div style={styles.labels}>
        <span style={styles.label}>
          {windowStart ? new Date(windowStart).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
        </span>
        {currentTime && (
          <span style={{ ...styles.label, color: CURSOR_COLOR, fontWeight: 700 }}>
            ▶ {new Date(currentTime).toLocaleTimeString()}
          </span>
        )}
        <span style={styles.label}>
          {windowEnd ? new Date(windowEnd).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
        </span>
      </div>

      {/* Legend */}
      <div style={styles.legend}>
        <LegendItem color={RECORDING_COLOR} label="Normal" />
        <LegendItem color={MOTION_COLOR} label="Motion" />
        <LegendItem color={ALARM_COLOR} label="Alarm" />
        <LegendItem color={GAP_COLOR} label="No recording" opacity={0.5} />
      </div>
    </div>
  )
}

function LegendItem({ color, label, opacity = 1 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <div style={{
        width: 12,
        height: 12,
        borderRadius: 2,
        backgroundColor: color,
        opacity,
        border: '1px solid #374151',
      }} />
      <span style={{ color: '#9ca3af', fontSize: '0.7rem' }}>{label}</span>
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    padding: '8px 0',
  },
  bar: {
    position: 'relative',
    height: 24,
    backgroundColor: '#111827',
    borderRadius: 4,
    overflow: 'hidden',
    cursor: 'pointer',
    border: '1px solid #374151',
  },
  loadingBar: {
    height: 24,
    backgroundColor: '#111827',
    borderRadius: 4,
    overflow: 'hidden',
    border: '1px solid #374151',
  },
  loadingPulse: {
    height: '100%',
    width: '30%',
    backgroundColor: '#374151',
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  labels: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    color: '#6b7280',
    fontSize: '0.7rem',
  },
  legend: {
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap',
  },
}
