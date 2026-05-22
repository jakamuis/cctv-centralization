import React from 'react'

export default function RefreshButton({ onClick, disabled }) {
  return (
    <button className="refresh" onClick={onClick} disabled={disabled} title="Refresh">
      ⟳ Refresh
    </button>
  )
}
