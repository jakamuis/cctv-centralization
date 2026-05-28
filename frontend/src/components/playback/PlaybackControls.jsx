/**
 * PlaybackControls.jsx
 *
 * Playback control bar: channel selector, time range picker, search button.
 *
 * Props:
 *   nvrs          {Array}    list of discovered NVRs
 *   selectedNvr   {object}   currently selected NVR
 *   onNvrChange   {function}
 *   channel       {number}   selected channel (1-based)
 *   onChannelChange {function}
 *   startTime     {string}   ISO time string (HH:MM)
 *   endTime       {string}   ISO time string (HH:MM)
 *   onStartTimeChange {function}
 *   onEndTimeChange   {function}
 *   onSearch      {function} called when user clicks Search
 *   onPlay        {function} called when user clicks Play
 *   loading       {boolean}
 *   hasResults    {boolean}
 */

import React from 'react'

export default function PlaybackControls({
  nvrs = [],
  selectedNvr,
  onNvrChange,
  channel,
  onChannelChange,
  startTime,
  endTime,
  onStartTimeChange,
  onEndTimeChange,
  onSearch,
  onPlay,
  loading = false,
  hasResults = false,
  timezone = 'WIB',
}) {
  return (
    <div style={styles.container}>
      {/* NVR selector */}
      <div style={styles.field}>
        <label style={styles.label}>Device</label>
        <select
          style={styles.select}
          value={selectedNvr?.id || ''}
          onChange={e => {
            const nvr = nvrs.find(n => n.id === e.target.value)
            onNvrChange?.(nvr || null)
          }}
        >
          <option value="">— Select NVR —</option>
          {nvrs.map(nvr => (
            <option key={nvr.id} value={nvr.id}>
              {nvr.device_name || nvr.nvr_ip} ({nvr.code})
            </option>
          ))}
        </select>
      </div>

      {/* Channel selector */}
      <div style={styles.field}>
        <label style={styles.label}>Channel</label>
        <input
          type="number"
          min={1}
          max={64}
          value={channel}
          onChange={e => onChannelChange?.(parseInt(e.target.value, 10) || 1)}
          style={{ ...styles.select, width: 70 }}
        />
      </div>

      {/* Time range */}
      <div style={styles.field}>
        <label style={styles.label}>From ({timezone})</label>
        <input
          type="time"
          value={startTime}
          onChange={e => onStartTimeChange?.(e.target.value)}
          style={styles.timeInput}
        />
      </div>

      <div style={styles.field}>
        <label style={styles.label}>To ({timezone})</label>
        <input
          type="time"
          value={endTime}
          onChange={e => onEndTimeChange?.(e.target.value)}
          style={styles.timeInput}
        />
      </div>

      {/* Actions */}
      <div style={styles.actions}>
        <button
          style={{
            ...styles.btn,
            backgroundColor: '#374151',
            opacity: loading || !selectedNvr ? 0.5 : 1,
          }}
          onClick={onSearch}
          disabled={loading || !selectedNvr}
        >
          {loading ? '⟳ Searching…' : '🔍 Search'}
        </button>

        {hasResults && (
          <button
            style={{
              ...styles.btn,
              backgroundColor: '#3b82f6',
            }}
            onClick={onPlay}
            disabled={loading}
          >
            ▶ Play
          </button>
        )}
      </div>
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 12,
    alignItems: 'flex-end',
    padding: '12px 16px',
    backgroundColor: '#1f2937',
    borderRadius: 8,
    border: '1px solid #374151',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  label: {
    color: '#9ca3af',
    fontSize: '0.7rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  select: {
    backgroundColor: '#111827',
    color: '#f9fafb',
    border: '1px solid #374151',
    borderRadius: 6,
    padding: '6px 10px',
    fontSize: '0.875rem',
    outline: 'none',
    cursor: 'pointer',
    minWidth: 180,
  },
  timeInput: {
    backgroundColor: '#111827',
    color: '#f9fafb',
    border: '1px solid #374151',
    borderRadius: 6,
    padding: '6px 10px',
    fontSize: '0.875rem',
    outline: 'none',
    width: 110,
  },
  actions: {
    display: 'flex',
    gap: 8,
    alignItems: 'flex-end',
  },
  btn: {
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '7px 16px',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'opacity 0.15s',
  },
}
