import React, { useEffect, useState } from 'react'
import { discoveryApi } from '../api'

// Status badge colours
const STATUS_COLORS = {
  synced:      { bg: '#d1fae5', text: '#065f46' },
  unreachable: { bg: '#fee2e2', text: '#991b1b' },
  auth_error:  { bg: '#fef3c7', text: '#92400e' },
  failed:      { bg: '#fee2e2', text: '#991b1b' },
}

function StatusBadge({ status }) {
  const colors = STATUS_COLORS[status] || { bg: '#f3f4f6', text: '#374151' }
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: '9999px',
      fontSize: '0.75rem',
      fontWeight: 600,
      backgroundColor: colors.bg,
      color: colors.text,
    }}>
      {status || '—'}
    </span>
  )
}

export default function Discovery() {
  const [nvrs, setNvrs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    discoveryApi.getNvrs()
      .then(data => {
        setNvrs(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <div style={{ padding: '24px', fontFamily: 'sans-serif' }}>
      <h2 style={{ marginBottom: '4px', fontSize: '1.25rem', fontWeight: 700 }}>
        Discovered NVR Devices
      </h2>
      <p style={{ marginBottom: '20px', color: '#6b7280', fontSize: '0.875rem' }}>
        Synced from Google Sheet CSV via Hikvision ISAPI
      </p>

      {loading && (
        <p style={{ color: '#6b7280' }}>Loading…</p>
      )}

      {error && (
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          borderRadius: '6px',
          marginBottom: '16px',
          fontSize: '0.875rem',
        }}>
          Error: {error}
        </div>
      )}

      {!loading && !error && nvrs.length === 0 && (
        <div style={{
          padding: '32px',
          textAlign: 'center',
          color: '#9ca3af',
          border: '1px dashed #d1d5db',
          borderRadius: '8px',
        }}>
          No NVR devices found. Run a sync first via{' '}
          <code style={{ fontSize: '0.8rem', background: '#f3f4f6', padding: '2px 6px', borderRadius: '4px' }}>
            POST /api/v1/discovery/sync
          </code>
        </div>
      )}

      {!loading && nvrs.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '0.875rem',
          }}>
            <thead>
              <tr style={{ backgroundColor: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                {['Site Code', 'Branch Name', 'IP Address', 'HTTP Port', 'Model', 'Serial', 'Firmware', 'Status', 'Last Synced'].map(h => (
                  <th key={h} style={{
                    padding: '10px 14px',
                    textAlign: 'left',
                    fontWeight: 600,
                    color: '#374151',
                    whiteSpace: 'nowrap',
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {nvrs.map((nvr, i) => (
                <tr key={nvr.id} style={{
                  borderBottom: '1px solid #e5e7eb',
                  backgroundColor: i % 2 === 0 ? '#ffffff' : '#f9fafb',
                }}>
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: '#111827' }}>
                    {nvr.site_code || '—'}
                  </td>
                  <td style={{ padding: '10px 14px', color: '#374151' }}>
                    {nvr.branch_name || '—'}
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: '#1d4ed8' }}>
                    {nvr.nvr_ip || '—'}
                  </td>
                  <td style={{ padding: '10px 14px', color: '#6b7280' }}>
                    {nvr.http_port}
                  </td>
                  <td style={{ padding: '10px 14px', color: '#374151' }}>
                    {nvr.model || '—'}
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontSize: '0.75rem', color: '#6b7280' }}>
                    {nvr.serial_number || '—'}
                  </td>
                  <td style={{ padding: '10px 14px', color: '#6b7280' }}>
                    {nvr.firmware_version || '—'}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <StatusBadge status={nvr.sync_status} />
                  </td>
                  <td style={{ padding: '10px 14px', color: '#9ca3af', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                    {nvr.last_synced_at
                      ? new Date(nvr.last_synced_at).toLocaleString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ marginTop: '10px', color: '#9ca3af', fontSize: '0.75rem' }}>
            {nvrs.length} device{nvrs.length !== 1 ? 's' : ''} found
          </p>
        </div>
      )}
    </div>
  )
}
