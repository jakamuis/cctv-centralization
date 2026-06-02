/**
 * App.jsx — Root application component
 *
 * Handles:
 *   - Auth gate: show Login page if not authenticated
 *   - Loading spinner while verifying existing token
 *   - Renders the main MonitoringApp once authenticated
 *   - Passes user/logout down to MonitoringApp
 */

import React from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import Login from './pages/Login'
import MonitoringApp from './pages/Monitoring'

// ─── Inner app (needs auth context) ──────────────────────────────────────────

function AppInner() {
  const { isAuthenticated, loading, user, logout } = useAuth()

  // While verifying existing token, show a minimal loading screen
  if (loading) {
    return (
      <div className="w-screen h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-muted-foreground">Loading…</span>
        </div>
      </div>
    )
  }

  // Not authenticated → show login page
  if (!isAuthenticated) {
    return <Login />
  }

  // Authenticated → show main app, pass user + logout
  return <MonitoringApp user={user} onLogout={logout} />
}

// ─── Root export ──────────────────────────────────────────────────────────────

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppInner />
      </AuthProvider>
    </ThemeProvider>
  )
}
