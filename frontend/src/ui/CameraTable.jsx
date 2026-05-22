import React, { useState } from 'react'
import LiveGrid from './LiveGrid'
import LivePlayer from './LivePlayer'

function StatusBadge({ status }) {
  const s = (status || '').toLowerCase()
  const cls = s === 'online' ? 'badge online' : s === 'offline' ? 'badge offline' : 'badge'
  return <span className={cls}>{s || 'unknown'}</span>
}

function EnabledBadge({ enabled }) {
  return <span className={enabled ? 'badge enabled' : 'badge disabled'}>{enabled ? 'enabled' : 'disabled'}</span>
}

/**
 * Modal wrapper — renders children in a centered overlay.
 * Click backdrop to close.
 */
function PlayerModal({ cam, onClose }) {
  if (!cam) return null
  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-body" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontWeight: 600 }}>{cam.name || 'Live'}</span>
          <button className="icon" onClick={onClose} title="Close">✕</button>
        </div>
        <LivePlayer cameraId={cam.id} title={cam.name || 'Live'} muted={true} />
      </div>
    </div>
  )
}

export default function CameraTable({ items, loading, error, page, totalPages, onPageChange }) {
  const [showGrid, setShowGrid] = useState(false)
  const [gridCameras, setGridCameras] = useState([])
  const [activeCam, setActiveCam] = useState(null)   // used for both Preview and Open Stream

  const openGrid = () => {
    setGridCameras(items.slice(0, 4))
    setShowGrid(true)
  }

  if (loading) return <div className="muted">Loading cameras...</div>
  if (error) return <div className="error">{error}</div>
  if (!items || items.length === 0) return <div className="muted">No cameras</div>

  return (
    <div className="camera-table">
      <div className="table-actions">
        <button onClick={openGrid} disabled={!items || items.length === 0}>Open 2×2 Grid (substream)</button>
      </div>
      <div className="grid grid-3">
        {items.map(cam => (
          <div className="card" key={cam.id}>
            <div className="card-header">
              <div className="title">{cam.name || 'Unnamed'}</div>
              <div className="badges">
                <StatusBadge status={cam.status} />
                <EnabledBadge enabled={cam.enabled} />
              </div>
            </div>
            <div className="card-body">
              <div className="meta-row"><span>Stream</span><span className="mono">{cam.stream_name}</span></div>
              <div className="meta-row"><span>RTSP Ch</span><span className="mono">{cam.rtsp_channel}</span></div>
            </div>
            <div className="card-actions" style={{ gap: 8 }}>
              {/* Both buttons open the same LivePlayer modal — single playback engine */}
              <button onClick={() => setActiveCam(cam)}>Preview Live</button>
              <button className="primary" onClick={() => setActiveCam(cam)} disabled={!cam.stream_name}>
                Open Stream
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="pagination">
        <button onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page <= 1}>Prev</button>
        <span>Page {page} / {totalPages}</span>
        <button onClick={() => onPageChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages}>Next</button>
      </div>

      {/* 2×2 grid panel */}
      <LiveGrid cameras={gridCameras} visible={showGrid} onClose={() => setShowGrid(false)} />

      {/* Unified player modal — same engine for Preview and Open Stream */}
      <PlayerModal cam={activeCam} onClose={() => setActiveCam(null)} />
    </div>
  )
}
