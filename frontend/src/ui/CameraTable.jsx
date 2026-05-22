import React from 'react'

function StatusBadge({ status }) {
  const s = (status || '').toLowerCase()
  const cls = s === 'online' ? 'badge online' : s === 'offline' ? 'badge offline' : 'badge'
  return <span className={cls}>{s || 'unknown'}</span>
}

function EnabledBadge({ enabled }) {
  return <span className={enabled ? 'badge enabled' : 'badge disabled'}>{enabled ? 'enabled' : 'disabled'}</span>
}

export default function CameraTable({ items, loading, error, page, totalPages, onPageChange, onOpenStream }) {
  if (loading) return <div className="muted">Loading cameras...</div>
  if (error) return <div className="error">{error}</div>
  if (!items || items.length === 0) return <div className="muted">No cameras</div>

  return (
    <div className="camera-table">
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
            <div className="card-actions">
              <button className="primary" onClick={() => onOpenStream(cam.stream_name)} disabled={!cam.stream_name}>Open Stream</button>
            </div>
          </div>
        ))}
      </div>

      <div className="pagination">
        <button onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page <= 1}>Prev</button>
        <span>Page {page} / {totalPages}</span>
        <button onClick={() => onPageChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages}>Next</button>
      </div>
    </div>
  )
}
