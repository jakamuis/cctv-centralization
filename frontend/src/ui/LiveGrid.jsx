import React from 'react'
import LivePlayer from './LivePlayer'

// Simple 2x2 grid using substream to reduce bandwidth
export default function LiveGrid({ cameras, title = 'Live Grid', visible = true, onClose }) {
  if (!visible) return null
  const cams = (cameras || []).slice(0, 4)
  return (
    <div className="live-grid">
      <div className="live-grid-header">
        <div className="title">{title}</div>
        <div className="spacer" />
        {onClose && <button className="icon" onClick={onClose}>✕</button>}
      </div>
      <div className="grid grid-2">
        {cams.map(c => (
          <div className="grid-cell" key={c.id}>
            <LivePlayer cameraId={c.id} title={c.name || 'Camera'} useSubstream={true} muted={true} />
          </div>
        ))}
        {cams.length === 0 && <div className="muted">No cameras available</div>}
      </div>
    </div>
  )
}
