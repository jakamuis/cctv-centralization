import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Discovery from './pages/Discovery'
import Login from './pages/Login'
import { isAuthenticated, authApi, clearAuthToken } from './api'
import './styles.css'

const NAV_TABS = [
  { id: 'dashboard',  label: '📹 Dashboard' },
  { id: 'discovery',  label: '🔍 Discovery' },
]

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated())
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activePage, setActivePage] = useState('dashboard')

  useEffect(() => {
    const checkAuth = async () => {
      if (isAuthenticated()) {
        try {
          const userData = await authApi.getCurrentUser()
          setUser(userData)
          setAuthenticated(true)
        } catch (err) {
          console.error('Auth check failed:', err)
          clearAuthToken()
          setAuthenticated(false)
          setUser(null)
        }
      }
      setLoading(false)
    }
    checkAuth()
  }, [])

  const handleLoginSuccess = () => {
    setAuthenticated(true)
    window.location.reload()
  }

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch (err) {
      console.error('Logout error:', err)
    }
    setAuthenticated(false)
    setUser(null)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (!authenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6' }}>
      {/* Top nav bar */}
      <nav style={{
        backgroundColor: '#1f2937',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '48px',
      }}>
        {/* Left: tabs */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {NAV_TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActivePage(tab.id)}
              style={{
                padding: '6px 16px',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: activePage === tab.id ? 700 : 400,
                backgroundColor: activePage === tab.id ? '#3b82f6' : 'transparent',
                color: activePage === tab.id ? '#ffffff' : '#9ca3af',
                transition: 'background 0.15s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right: user + logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {user && (
            <span style={{ color: '#9ca3af', fontSize: '0.8rem' }}>
              {user.username}
            </span>
          )}
          <button
            onClick={handleLogout}
            style={{
              padding: '4px 12px',
              border: '1px solid #4b5563',
              borderRadius: '4px',
              backgroundColor: 'transparent',
              color: '#9ca3af',
              cursor: 'pointer',
              fontSize: '0.8rem',
            }}
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Page content */}
      <main>
        {activePage === 'dashboard' && <Dashboard user={user} onLogout={handleLogout} />}
        {activePage === 'discovery' && <Discovery />}
      </main>
    </div>
  )
}
