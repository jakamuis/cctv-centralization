/**
 * RecordingCalendar.jsx
 *
 * Date picker for selecting the playback date.
 * Shows a simple month calendar with the selected date highlighted.
 *
 * Props:
 *   selectedDate  {Date}     currently selected date
 *   onChange      {function} called with (Date) when user picks a date
 */

import React, { useState } from 'react'

const DAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]

function isSameDay(a, b) {
  if (!a || !b) return false
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function isToday(d) {
  return isSameDay(d, new Date())
}

export default function RecordingCalendar({ selectedDate, onChange }) {
  const today = new Date()
  const [viewYear, setViewYear] = useState(
    selectedDate ? selectedDate.getFullYear() : today.getFullYear()
  )
  const [viewMonth, setViewMonth] = useState(
    selectedDate ? selectedDate.getMonth() : today.getMonth()
  )

  const firstDay = new Date(viewYear, viewMonth, 1).getDay()
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate()

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1) }
    else setViewMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1) }
    else setViewMonth(m => m + 1)
  }

  const cells = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  return (
    <div style={styles.container}>
      {/* Month navigation */}
      <div style={styles.header}>
        <button style={styles.navBtn} onClick={prevMonth}>‹</button>
        <span style={styles.monthLabel}>
          {MONTHS[viewMonth]} {viewYear}
        </span>
        <button style={styles.navBtn} onClick={nextMonth}>›</button>
      </div>

      {/* Day headers */}
      <div style={styles.grid}>
        {DAYS.map(d => (
          <div key={d} style={styles.dayHeader}>{d}</div>
        ))}

        {/* Day cells */}
        {cells.map((day, i) => {
          if (!day) return <div key={`empty-${i}`} />
          const cellDate = new Date(viewYear, viewMonth, day)
          const selected = isSameDay(cellDate, selectedDate)
          const todayCell = isToday(cellDate)
          const future = cellDate > today

          return (
            <button
              key={day}
              disabled={future}
              onClick={() => !future && onChange?.(cellDate)}
              style={{
                ...styles.dayCell,
                backgroundColor: selected ? '#3b82f6' : todayCell ? '#1e3a5f' : 'transparent',
                color: future ? '#374151' : selected ? '#fff' : todayCell ? '#93c5fd' : '#d1d5db',
                cursor: future ? 'not-allowed' : 'pointer',
                fontWeight: selected || todayCell ? 700 : 400,
                border: todayCell && !selected ? '1px solid #3b82f6' : '1px solid transparent',
              }}
            >
              {day}
            </button>
          )
        })}
      </div>

      {/* Selected date display */}
      {selectedDate && (
        <div style={styles.selectedLabel}>
          📅 {selectedDate.toLocaleDateString(undefined, {
            weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
          })}
        </div>
      )}
    </div>
  )
}

const styles = {
  container: {
    backgroundColor: '#1f2937',
    borderRadius: 8,
    padding: 12,
    border: '1px solid #374151',
    userSelect: 'none',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  navBtn: {
    background: 'none',
    border: 'none',
    color: '#9ca3af',
    cursor: 'pointer',
    fontSize: '1.2rem',
    padding: '2px 8px',
    borderRadius: 4,
  },
  monthLabel: {
    color: '#f9fafb',
    fontSize: '0.875rem',
    fontWeight: 600,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: 2,
  },
  dayHeader: {
    color: '#6b7280',
    fontSize: '0.7rem',
    textAlign: 'center',
    padding: '4px 0',
    fontWeight: 600,
  },
  dayCell: {
    fontSize: '0.75rem',
    textAlign: 'center',
    padding: '5px 2px',
    borderRadius: 4,
    transition: 'background 0.1s',
    lineHeight: 1,
  },
  selectedLabel: {
    marginTop: 8,
    color: '#93c5fd',
    fontSize: '0.75rem',
    textAlign: 'center',
    borderTop: '1px solid #374151',
    paddingTop: 8,
  },
}
