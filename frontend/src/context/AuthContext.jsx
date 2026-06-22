/**
 * AuthContext — simple session/token management
 *
 * Provides:
 *   - user: { username, role } | null
 *   - token: string | null
 *   - login(username, password) → Promise
 *   - logout()
 *   - isAuthenticated: boolean
 *
 * Role values: "admin" | "operator" | "viewer"
 *
 * Token is persisted in localStorage via the existing api/index.js helpers.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi, getAuthToken, setAuthToken, clearAuthToken } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]   = useState(null)
  const [token, setToken] = useState(() => getAuthToken())
  const [loading, setLoading] = useState(true) // true while we verify existing token

  // On mount: if a token exists in localStorage, verify it by fetching /auth/me
  useEffect(() => {
    const existingToken = getAuthToken()
    if (!existingToken) {
      setLoading(false)
      return
    }

    authApi.getCurrentUser()
      .then((userData) => {
        setUser(normaliseUser(userData))
        setToken(existingToken)
      })
      .catch(() => {
        // Token is invalid/expired — clear it
        clearAuthToken()
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await authApi.login(username, password)
    // authApi.login already stores the token via setAuthToken()
    const newToken = data.access_token
    setToken(newToken)

    // Fetch full user profile to get role
    try {
      const userData = await authApi.getCurrentUser()
      setUser(normaliseUser(userData))
    } catch {
      // Fallback: build minimal user from login response
      setUser(normaliseUser(data.user || { username, role: 'viewer' }))
    }

    return data
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore logout errors — always clear local state
    } finally {
      clearAuthToken()
      setToken(null)
      setUser(null)
    }
  }, [])

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Normalise whatever the backend returns into { username, role, email }.
 *
 * The backend stores roles as uppercase strings:
 *   SUPER_ADMIN → "admin"
 *   OPERATOR    → "operator"
 *   VIEWER      → "viewer"
 *
 * The backend /auth/me returns:
 *   { id, username, email, roles: ["SUPER_ADMIN"] }   ← roles is an array of strings
 */
function normaliseUser(raw) {
  if (!raw) return null

  // Extract the raw role name from whatever shape the backend returns
  let rawRole =
    typeof raw.role === 'string'
      ? raw.role
      : raw.role?.name ||
        (Array.isArray(raw.roles) ? raw.roles[0] : null) ||
        'VIEWER'

  // Map backend uppercase role names → frontend lowercase role keys
  const role = mapBackendRole(rawRole)

  return {
    username:  raw.username  || raw.email || 'user',
    full_name: raw.full_name || raw.username || raw.email || '',
    email:     raw.email     || '',
    role,
    rawRole:   rawRole,
    id:        raw.id || null,
  }
}

/**
 * Map backend role name → frontend role key.
 *
 * Backend roles:  SUPER_ADMIN, OPERATOR, VIEWER  (and legacy: admin, operator, viewer)
 * Frontend roles: admin, operator, viewer
 */
function mapBackendRole(roleName) {
  if (!roleName) return 'viewer'
  const r = roleName.toUpperCase()
  if (r === 'SUPER_ADMIN' || r === 'ADMIN') return 'admin'
  if (r === 'IT')                            return 'it'
  if (r === 'MANAGER')                       return 'manager'
  if (r === 'REGIONAL')                      return 'regional'
  if (r === 'OPERATOR')                      return 'operator'
  if (r === 'VIEWER')                        return 'viewer'
  const lower = roleName.toLowerCase()
  if (lower === 'admin')    return 'admin'
  if (lower === 'it')       return 'it'
  if (lower === 'manager')  return 'manager'
  if (lower === 'regional') return 'regional'
  if (lower === 'operator') return 'operator'
  return 'viewer'
}
