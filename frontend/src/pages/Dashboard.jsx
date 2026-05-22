import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import BranchSidebar from '../ui/BranchSidebar'
import CameraTable from '../ui/CameraTable'
import SearchBar from '../ui/SearchBar'
import RefreshButton from '../ui/RefreshButton'

export default function Dashboard({ user, onLogout }) {
  const [branches, setBranches] = useState([])
  const [branchesLoading, setBranchesLoading] = useState(false)
  const [branchesError, setBranchesError] = useState('')

  const [selectedBranchId, setSelectedBranchId] = useState(null)

  const [cameras, setCameras] = useState([])
  const [camerasLoading, setCamerasLoading] = useState(false)
  const [camerasError, setCamerasError] = useState('')

  const [query, setQuery] = useState('')
  const [enabledFilter, setEnabledFilter] = useState('all') // all | enabled | disabled
  const [statusFilter, setStatusFilter] = useState('all') // all | online | offline
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(12)

  useEffect(() => {
    async function loadBranches() {
      setBranchesLoading(true)
      setBranchesError('')
      try {
        const data = await api.getBranches()
        setBranches(data)
      } catch (e) {
        setBranchesError(e.message || 'Failed to load branches')
      } finally {
        setBranchesLoading(false)
      }
    }
    loadBranches()
  }, [])

  async function loadCameras(branchId = selectedBranchId) {
    setCamerasLoading(true)
    setCamerasError('')
    try {
      const data = branchId ? await api.getCamerasByBranch(branchId) : await api.getCameras()
      setCameras(Array.isArray(data) ? data : [])
    } catch (e) {
      setCamerasError(e.message || 'Failed to load cameras')
    } finally {
      setCamerasLoading(false)
    }
  }

  useEffect(() => {
    loadCameras()
  }, [selectedBranchId])

  function onSelectBranch(id) {
    setSelectedBranchId(id)
    setPage(1)
  }

  function onRefresh() {
    loadCameras()
  }

  const filtered = useMemo(() => {
    let list = cameras
    if (query) {
      const q = query.toLowerCase()
      list = list.filter(c =>
        (c.name || '').toLowerCase().includes(q) ||
        (c.stream_name || '').toLowerCase().includes(q) ||
        (c.rtsp_channel ? String(c.rtsp_channel) : '').toLowerCase().includes(q)
      )
    }
    if (enabledFilter !== 'all') {
      const flag = enabledFilter === 'enabled'
      list = list.filter(c => Boolean(c.enabled) === flag)
    }
    if (statusFilter !== 'all') {
      list = list.filter(c => (c.status || '').toLowerCase() === statusFilter)
    }
    return list
  }, [cameras, query, enabledFilter, statusFilter])

  const total = filtered.length
  const totalPages = Math.max(1, Math.ceil(total / perPage))
  const pageClamped = Math.min(page, totalPages)
  const paged = useMemo(() => {
    const start = (pageClamped - 1) * perPage
    const end = start + perPage
    return filtered.slice(start, end)
  }, [filtered, pageClamped, perPage])

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">Branches</div>
        <BranchSidebar
          branches={branches}
          loading={branchesLoading}
          error={branchesError}
          selectedId={selectedBranchId}
          onSelect={onSelectBranch}
        />
      </aside>
      <main className="content">
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
              <span style={{ fontWeight: '500' }}>
                {user.full_name || user.username}
              </span>
              {user.roles && user.roles.length > 0 && (
                <span style={{ fontSize: '0.85rem', color: '#666' }}>
                  {user.roles.join(', ')}
                </span>
              )}
            </div>
            <button onClick={onLogout} style={{ padding: '0.5rem 1rem' }}>
              Logout
            </button>
          </div>
        )}
        <div className="toolbar">
          <div className="filters">
            <SearchBar value={query} onChange={setQuery} placeholder="Search cameras..." />
            <select value={enabledFilter} onChange={e => { setEnabledFilter(e.target.value); setPage(1) }}>
              <option value="all">All</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
            <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}>
              <option value="all">All Status</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
            <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(1) }}>
              <option value={12}>12 / page</option>
              <option value={24}>24 / page</option>
              <option value={48}>48 / page</option>
            </select>
          </div>
          <RefreshButton onClick={onRefresh} disabled={camerasLoading} />
        </div>

        <CameraTable
          items={paged}
          loading={camerasLoading}
          error={camerasError}
          page={pageClamped}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </main>
    </div>
  )
}
