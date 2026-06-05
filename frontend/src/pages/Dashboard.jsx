import React, { useEffect, useMemo, useState } from 'react'
import { discoveryApi } from '../api'
import SearchBar from '../ui/SearchBar'
import RefreshButton from '../ui/RefreshButton'
import DiscoveryLivePlayer from '../ui/DiscoveryLivePlayer'

// ---------------------------------------------------------------------------
// Stat card (discovery summary bar)
// ---------------------------------------------------------------------------
function StatCard({ label, value, color }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '10px 24px',
      backgroundColor: '#ffffff',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      minWidth: '120px',
    }}>
      <span style={{ fontSize: '1.5rem', fontWeight: 700, color: color || '#111827' }}>
        {value === null ? '…' : value}
      </span>
      <span style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
        {label}
      </span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stream modal — wraps DiscoveryLivePlayer in the existing .modal CSS
// ---------------------------------------------------------------------------
function StreamModal({ streamName, title, onClose }) {
  if (!streamName) return null
  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-body" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontWeight: 600 }}>{title}</span>
          <button className="icon" onClick={onClose} title="Close">✕</button>
        </div>
        <DiscoveryLivePlayer streamName={streamName} title={title} />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Single channel card — with Open Stream button
// ---------------------------------------------------------------------------
function ChannelCard({ channel, nvr, onOpenStream }) {
  const isEnabled = channel.is_enabled !== false
  const [starting, setStarting] = useState(false)
  const [startErr, setStartErr] = useState(null)

  async function handleOpenStream() {
    setStarting(true)
    setStartErr(null)
    try {
      const data = await discoveryApi.startChannelStream(nvr.id, channel.channel_id)
      onOpenStream(data.stream_name, channel.channel_name || `Channel ${channel.channel_id}`)
    } catch (e) {
      setStartErr(e.message || 'Failed to start stream')
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="title">{channel.channel_name || `Channel ${channel.channel_id}`}</div>
        <div className="badges">
          <span className={isEnabled ? 'badge enabled' : 'badge disabled'}>
            {isEnabled ? 'enabled' : 'disabled'}
          </span>
        </div>
      </div>
      <div className="card-body">
        <div className="meta-row">
          <span>Channel</span>
          <span className="mono">{channel.channel_id}</span>
        </div>
        <div className="meta-row">
          <span>Site</span>
          <span className="mono">{nvr.code}</span>
        </div>
        {channel.ip_address && (
          <div className="meta-row">
            <span>IP</span>
            <span className="mono">{channel.ip_address}</span>
          </div>
        )}
        {channel.protocol && (
          <div className="meta-row">
            <span>Protocol</span>
            <span className="mono">{channel.protocol}</span>
          </div>
        )}
        {startErr && (
          <div className="meta-row" style={{ color: '#dc2626', fontSize: '0.75rem' }}>
            {startErr}
          </div>
        )}
      </div>
      <div className="card-actions">
        <button
          className="primary"
          onClick={handleOpenStream}
          disabled={starting || !isEnabled}
          title={!isEnabled ? 'Channel disabled' : 'Open live stream'}
        >
          {starting ? 'Starting…' : 'Open Stream'}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// NVR group header
// ---------------------------------------------------------------------------
function NvrGroupHeader({ nvr, channelCount }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '10px 0 6px',
      borderBottom: '2px solid #e5e7eb',
      marginBottom: '12px',
      marginTop: '8px',
    }}>
      <span style={{ fontWeight: 700, fontSize: '1rem', color: '#111827' }}>
        {nvr.branch_name || nvr.code}
      </span>
      <span style={{ fontSize: '0.8rem', color: '#6b7280', fontFamily: 'monospace' }}>
        {nvr.nvr_ip}:{nvr.http_port}
      </span>
      <span style={{
        fontSize: '0.75rem',
        backgroundColor: '#dbeafe',
        color: '#1d4ed8',
        padding: '2px 8px',
        borderRadius: '9999px',
        fontWeight: 600,
      }}>
        {channelCount} ch
      </span>
      <span style={{
        fontSize: '0.75rem',
        backgroundColor: nvr.sync_status === 'synced' ? '#d1fae5' : '#fee2e2',
        color: nvr.sync_status === 'synced' ? '#065f46' : '#991b1b',
        padding: '2px 8px',
        borderRadius: '9999px',
        fontWeight: 600,
      }}>
        {nvr.sync_status}
      </span>
      {nvr.model && (
        <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
          {nvr.model}
        </span>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------
export default function Dashboard({ user, onLogout }) {
  const [nvrGroups, setNvrGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [syncing, setSyncing] = useState(false)

  // Sidebar: null = all NVRs, or nvr.id
  const [selectedNvrId, setSelectedNvrId] = useState(null)

  // Stream modal: { streamName, title } | null
  const [activeStream, setActiveStream] = useState(null)

  // Search
  const [query, setQuery] = useState('')

  const stats = useMemo(() => ({
    total: nvrGroups.length,
    online: nvrGroups.filter(g => g.nvr.sync_status === 'synced').length,
    totalChannels: nvrGroups.reduce((s, g) => s + g.channels.length, 0),
  }), [nvrGroups])

  async function handleSyncAll() {
    setSyncing(true)
    try {
      await discoveryApi.syncAll()
      await loadAll()
    } finally {
      setSyncing(false)
    }
  }

  async function loadAll() {
    setLoading(true)
    setError(null)
    try {
      const nvrs = await discoveryApi.getNvrs()
      const results = await Promise.allSettled(
        nvrs.map(nvr => discoveryApi.getChannels(nvr.id))
      )
      setNvrGroups(nvrs.map((nvr, i) => ({
        nvr,
        channels: results[i].status === 'fulfilled' ? (results[i].value.channels || []) : [],
      })))
    } catch (e) {
      setError(e.message || 'Failed to load discovery data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll() }, [])

  const visibleGroups = useMemo(() => {
    let groups = selectedNvrId
      ? nvrGroups.filter(g => g.nvr.id === selectedNvrId)
      : nvrGroups
    if (query.trim()) {
      const q = query.toLowerCase()
      groups = groups.map(g => ({
        ...g,
        channels: g.channels.filter(ch =>
          (ch.channel_name || '').toLowerCase().includes(q) ||
          (ch.channel_id || '').toLowerCase().includes(q) ||
          (ch.ip_address || '').toLowerCase().includes(q) ||
          (g.nvr.code || '').toLowerCase().includes(q) ||
          (g.nvr.branch_name || '').toLowerCase().includes(q)
        ),
      })).filter(g => g.channels.length > 0)
    }
    return groups
  }, [nvrGroups, selectedNvrId, query])

  const totalVisible = visibleGroups.reduce((s, g) => s + g.channels.length, 0)

  return (
    <div className="layout">

      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-header">NVR Devices</div>
        {loading && <div className="muted">Loading…</div>}
        {!loading && nvrGroups.length === 0 && (
          <div className="muted">No devices synced yet</div>
        )}
        {!loading && nvrGroups.length > 0 && (
          <ul className="branch-list">
            <li className={!selectedNvrId ? 'active' : ''}>
              <button className="link" onClick={() => setSelectedNvrId(null)}>
                All NVRs ({stats.totalChannels} ch)
              </button>
            </li>
            {nvrGroups.map(({ nvr, channels }) => (
              <li key={nvr.id} className={selectedNvrId === nvr.id ? 'active' : ''}>
                <button className="branch-item" onClick={() => setSelectedNvrId(nvr.id)}>
                  <div className="branch-name">{nvr.branch_name || nvr.code}</div>
                  <div className="branch-meta">
                    <span className="code">{nvr.code}</span>
                    <span className="location">{channels.length} channels</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* ── Main content ── */}
      <main className="content">

        {/* User header */}
        {user && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.75rem 1rem',
            background: '#f8f9fa',
            borderBottom: '1px solid #dee2e6',
            marginBottom: '1rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span style={{ fontWeight: '500' }}>{user.full_name || user.username}</span>
              {user.roles && user.roles.length > 0 && (
                <span style={{ fontSize: '0.85rem', color: '#666' }}>{user.roles.join(', ')}</span>
              )}
            </div>
            <button onClick={onLogout} style={{ padding: '0.5rem 1rem' }}>Logout</button>
          </div>
        )}

        {/* Stats bar */}
        <div style={{
          display: 'flex',
          gap: '12px',
          padding: '12px 16px',
          backgroundColor: '#f9fafb',
          borderBottom: '1px solid #e5e7eb',
          flexWrap: 'wrap',
        }}>
          <StatCard label="Synced NVRs"    value={loading ? null : stats.total}         color="#1d4ed8" />
          <StatCard label="Online Devices" value={loading ? null : stats.online}        color="#059669" />
          <StatCard label="Total Channels" value={loading ? null : stats.totalChannels} color="#7c3aed" />
        </div>

        {/* Toolbar */}
        <div className="toolbar">
          <div className="filters">
            <SearchBar value={query} onChange={setQuery} placeholder="Search channels, sites…" />
          </div>
          <button
            onClick={handleSyncAll}
            disabled={syncing || loading}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '6px 12px', fontSize: '0.75rem', borderRadius: '6px',
              backgroundColor: syncing ? '#059669' : '#10b981',
              color: '#fff', border: 'none', cursor: 'pointer', opacity: (syncing || loading) ? 0.6 : 1,
            }}
          >
            {syncing ? '⟳ Syncing…' : '⟳ Sync All'}
          </button>
          <RefreshButton onClick={loadAll} disabled={loading} />
        </div>

        {error && <div className="error" style={{ margin: '16px' }}>{error}</div>}
        {loading && <div className="muted" style={{ padding: '32px 16px' }}>Loading channels…</div>}

        {!loading && !error && totalVisible === 0 && (
          <div className="muted" style={{ padding: '32px 16px', textAlign: 'center' }}>
            {query ? 'No channels match your search.' : 'No channels found. Run a sync first.'}
          </div>
        )}

        {/* Channel cards grouped by NVR */}
        {!loading && !error && visibleGroups.map(({ nvr, channels }) =>
          channels.length > 0 && (
            <div key={nvr.id} style={{ padding: '0 16px 16px' }}>
              <NvrGroupHeader nvr={nvr} channelCount={channels.length} />
              <div className="grid grid-3">
                {channels.map(ch => (
                  <ChannelCard
                    key={ch.id}
                    channel={ch}
                    nvr={nvr}
                    onOpenStream={(streamName, title) => setActiveStream({ streamName, title })}
                  />
                ))}
              </div>
            </div>
          )
        )}

        {!loading && totalVisible > 0 && (
          <div style={{ padding: '8px 16px 24px', color: '#9ca3af', fontSize: '0.75rem' }}>
            Showing {totalVisible} channel{totalVisible !== 1 ? 's' : ''}
            {selectedNvrId
              ? ' from 1 NVR'
              : ` across ${visibleGroups.length} NVR${visibleGroups.length !== 1 ? 's' : ''}`}
          </div>
        )}

      </main>

      {/* Stream player modal — rendered outside <main> so it overlays everything */}
      <StreamModal
        streamName={activeStream?.streamName}
        title={activeStream?.title}
        onClose={() => setActiveStream(null)}
      />

    </div>
  )
}
