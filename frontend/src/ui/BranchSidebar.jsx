import React from 'react'

export default function BranchSidebar({ branches, loading, error, selectedId, onSelect }) {
  if (loading) return <div className="muted">Loading branches...</div>
  if (error) return <div className="error">{error}</div>
  if (!branches || branches.length === 0) return <div className="muted">No branches</div>

  return (
    <ul className="branch-list">
      <li className={!selectedId ? 'active' : ''}>
        <button className="link" onClick={() => onSelect(null)}>All branches</button>
      </li>
      {branches.map(b => (
        <li key={b.id} className={selectedId === b.id ? 'active' : ''}>
          <button className="branch-item" onClick={() => onSelect(b.id)}>
            <div className="branch-name">{b.name}</div>
            <div className="branch-meta">
              <span className="code">{b.code}</span>
              {b.location ? <span className="location">{b.location}</span> : null}
            </div>
          </button>
        </li>
      ))}
    </ul>
  )
}
