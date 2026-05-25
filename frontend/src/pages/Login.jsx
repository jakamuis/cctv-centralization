/**
 * Login.jsx — Login page styled to match the dark Monitoring UI
 *
 * Uses useAuth() from AuthContext — no props needed.
 */

import React, { useState } from 'react'
import { Camera, Eye, EyeOff, LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      // AuthContext will set isAuthenticated → App.jsx will render MonitoringApp
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="dark w-screen h-screen flex items-center justify-center bg-[#0d1117] font-['Inter',sans-serif]">
      <div className="w-full max-w-sm mx-4">

        {/* Card */}
        <div className="bg-[#141d2b] border border-[rgba(255,255,255,0.07)] rounded-xl shadow-2xl overflow-hidden">

          {/* Header */}
          <div className="px-8 pt-8 pb-6 border-b border-[rgba(255,255,255,0.07)]">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <Camera size={18} className="text-white" />
              </div>
              <div>
                <h1 className="text-base font-semibold text-white leading-tight">SAMATOR</h1>
                <p className="text-[11px] text-[#64748b] leading-tight">CCTV Centralization</p>
              </div>
            </div>
            <h2 className="text-xl font-semibold text-white">Sign in</h2>
            <p className="text-xs text-[#64748b] mt-1">Enter your credentials to access the system</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-8 py-6 space-y-4">

            {/* Username */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[#94a3b8]">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                disabled={loading}
                placeholder="admin"
                className="
                  w-full px-3 py-2.5 rounded-lg text-sm
                  bg-[#1e2a3b] border border-[rgba(255,255,255,0.07)]
                  text-white placeholder-[#475569]
                  focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[#94a3b8]">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="••••••••"
                  className="
                    w-full px-3 py-2.5 pr-10 rounded-lg text-sm
                    bg-[#1e2a3b] border border-[rgba(255,255,255,0.07)]
                    text-white placeholder-[#475569]
                    focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50
                    disabled:opacity-50 disabled:cursor-not-allowed
                    transition-colors
                  "
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#475569] hover:text-[#94a3b8] transition-colors"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                <span className="text-red-400 text-xs leading-relaxed">{error}</span>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="
                w-full flex items-center justify-center gap-2
                px-4 py-2.5 rounded-lg text-sm font-medium
                bg-blue-600 hover:bg-blue-500
                disabled:opacity-50 disabled:cursor-not-allowed
                text-white transition-colors
                focus:outline-none focus:ring-2 focus:ring-blue-500/50
              "
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  <LogIn size={15} />
                  Sign in
                </>
              )}
            </button>
          </form>

          {/* Demo accounts hint */}
          <div className="px-8 pb-6">
            <div className="px-3 py-3 bg-[#1a2436] border border-[rgba(255,255,255,0.05)] rounded-lg space-y-1.5">
              <p className="text-[11px] text-[#94a3b8] font-medium mb-2">Demo accounts:</p>
              {[
                { user: 'admin',    pass: 'admin123',    label: 'Admin',    color: 'text-blue-400' },
                { user: 'operator', pass: 'operator123', label: 'Operator', color: 'text-emerald-400' },
                { user: 'viewer',   pass: 'viewer123',   label: 'Viewer',   color: 'text-amber-400' },
              ].map(({ user, pass, label, color }) => (
                <button
                  key={user}
                  type="button"
                  onClick={() => { setUsername(user); setPassword(pass); }}
                  className="w-full flex items-center justify-between px-2 py-1 rounded hover:bg-[#1e2a3b] transition-colors group"
                >
                  <span className={`text-[11px] font-medium ${color}`}>{label}</span>
                  <span className="text-[11px] text-[#475569] font-mono group-hover:text-[#64748b]">
                    {user} / {pass}
                  </span>
                </button>
              ))}
              <p className="text-[10px] text-[#334155] pt-1">Click a row to auto-fill credentials</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-[11px] text-[#334155] mt-5">
          SAMATOR CCTV Centralization System
        </p>
      </div>
    </div>
  )
}
