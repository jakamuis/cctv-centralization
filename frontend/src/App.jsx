import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import { isAuthenticated, authApi, clearAuthToken } from './api'
import './styles.css'

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated())
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if token is valid on mount
    const checkAuth = async () => {
      if (isAuthenticated()) {
        try {
          const userData = await authApi.getCurrentUser()
          setUser(userData)
          setAuthenticated(true)
        } catch (err) {
          // Token is invalid or expired
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
    // Reload to fetch user data
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
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
      }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (!authenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />
  }

  return <Dashboard user={user} onLogout={handleLogout} />
}
