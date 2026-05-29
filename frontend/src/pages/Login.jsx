import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass]  = useState(false)
  const [loading, setLoading]    = useState(false)
  const [error, setError]        = useState('')

  const handleSubmit = async (e) => {
    e?.preventDefault()
    if (!username || !password) return
    setError('')
    setLoading(true)
    try {
      await login(username, password)
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const fillDemo = (u, p) => {
    setUsername(u)
    setPassword(p)
    setError('')
  }

  return (
    <>
      <style>{`
        body {
          background:
            radial-gradient(circle at top left, rgba(37,99,235,0.18), transparent 30%),
            radial-gradient(circle at bottom right, rgba(59,130,246,0.08), transparent 25%),
            #020817;
          overflow: hidden;
        }
        .glass {
          background: rgba(10, 15, 30, 0.82);
          backdrop-filter: blur(18px);
          border: 1px solid rgba(59, 130, 246, 0.15);
          box-shadow: 0 0 0 1px rgba(255,255,255,0.02), 0 20px 60px rgba(0,0,0,0.45);
        }
        .input-dark {
          background: rgba(15, 23, 42, 0.7);
          border: 1px solid rgba(148, 163, 184, 0.12);
          transition: all 0.2s ease;
        }
        .input-dark:focus-within {
          border-color: rgba(59,130,246,0.55);
          box-shadow: 0 0 0 4px rgba(59,130,246,0.12);
        }
        .login-btn {
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          transition: all 0.2s ease;
        }
        .login-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 10px 30px rgba(37,99,235,0.35);
        }
        .login-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }
        .account-row {
          transition: background 0.18s;
          cursor: pointer;
        }
        .account-row:hover {
          background: rgba(255,255,255,0.03);
        }
        .cityline {
          background:
            linear-gradient(to top, rgba(37,99,235,0.12), transparent),
            url('https://images.unsplash.com/photo-1514565131-fce0801e5785?q=80&w=1200&auto=format&fit=crop');
          background-size: cover;
          background-position: center bottom;
          opacity: 0.18;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      <div className="min-h-screen flex items-center justify-center text-white font-sans">
        <div className="glass w-[1200px] h-[760px] rounded-[32px] overflow-hidden flex">

          {/* LEFT */}
          <div className="relative w-[46%] border-r border-white/5 overflow-hidden">
            <div className="absolute inset-0 cityline" />
            <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent" />

            <div className="relative z-10 h-full flex flex-col items-center justify-center px-16">
              <img src="/samator-logo.png" alt="SAMATOR" className="w-[280px] mb-8" />

              <div className="w-24 h-[3px] bg-blue-500 rounded-full mb-10"
                   style={{ boxShadow: '0 0 20px rgba(59,130,246,0.8)' }} />

              <div className="text-center">
                <p className="text-2xl font-semibold tracking-wide text-white mb-3">SAMATOR</p>
                <p className="text-base text-slate-300 mb-8">CCTV Centralization</p>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Centralized Monitoring.<br />Smarter Security.
                </p>
              </div>
            </div>
          </div>

          {/* RIGHT */}
          <div className="flex-1 flex items-center justify-center px-16">
            <div className="w-full max-w-[520px]">

              <h1 className="text-4xl font-bold tracking-tight mb-2">Sign in</h1>
              <p className="text-slate-400 text-sm mb-8">
                Enter your credentials to access the system
              </p>

              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Username */}
                <div>
                  <label className="block text-sm text-slate-300 mb-2">Username</label>
                  <div className="input-dark rounded-xl h-12 flex items-center px-4">
                    <svg className="w-5 h-5 text-slate-500 mr-3 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5.121 17.804A9 9 0 1118.88 17.8M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    <input
                      type="text"
                      value={username}
                      onChange={e => setUsername(e.target.value)}
                      placeholder="Enter username"
                      autoComplete="off"
                      disabled={loading}
                      required
                      autoFocus
                      className="bg-transparent w-full text-sm placeholder:text-slate-500 focus:outline-none text-white"
                    />
                  </div>
                </div>

                {/* Password */}
                <div>
                  <label className="block text-sm text-slate-300 mb-2">Password</label>
                  <div className="input-dark rounded-xl h-12 flex items-center px-4">
                    <svg className="w-5 h-5 text-slate-500 mr-3 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m6-8V7a6 6 0 10-12 0v2m-2 0h16v10H4V9z"/>
                    </svg>
                    <input
                      type={showPass ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="Enter password"
                      disabled={loading}
                      required
                      className="bg-transparent w-full text-sm placeholder:text-slate-500 focus:outline-none text-white"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass(v => !v)}
                      tabIndex={-1}
                      className="ml-3 shrink-0 text-slate-500 hover:text-slate-300 transition"
                    >
                      {showPass ? (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
                          <line x1="1" y1="1" x2="23" y2="23"/>
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M1.458 12C2.732 7.943 6.523 5 12 5c5.477 0 9.268 2.943 10.542 7-1.274 4.057-5.065 7-10.542 7-5.477 0-9.268-2.943-10.542-7z"/>
                          <circle cx="12" cy="12" r="3"/>
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <div className="px-4 py-3 rounded-xl text-base text-red-400"
                       style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)' }}>
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading || !username || !password}
                  className="login-btn w-full h-11 rounded-xl text-base font-semibold flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <div style={{
                        width: 22, height: 22,
                        border: '2px solid rgba(255,255,255,0.3)',
                        borderTopColor: '#fff',
                        borderRadius: '50%',
                        animation: 'spin 0.7s linear infinite',
                      }} />
                      Signing in…
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 3h6v18h-6M10 17l5-5-5-5M15 12H3"/>
                      </svg>
                      Sign in
                    </>
                  )}
                </button>
              </form>

              {/* Demo accounts */}
              <div className="mt-8">
                <div className="flex items-center gap-4 mb-4">
                  <div className="flex-1 h-px bg-white/10" />
                  <span className="text-slate-500 text-xs uppercase tracking-[0.3em]">Demo Accounts</span>
                  <div className="flex-1 h-px bg-white/10" />
                </div>

                <div className="border border-white/5 rounded-3xl overflow-hidden bg-white/[0.02]">
                  {[
                    { user: 'admin',    pass: 'admin123',    label: 'Admin',    sub: 'Full access',          avatar: 'A', color: 'text-blue-400',    bg: 'bg-blue-500/20'    },
                    { user: 'operator', pass: 'operator123', label: 'Operator', sub: 'Operational access',   avatar: 'O', color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
                    { user: 'viewer',   pass: 'viewer123',   label: 'Viewer',   sub: 'Read-only monitoring', avatar: 'V', color: 'text-yellow-400',  bg: 'bg-yellow-500/20'  },
                  ].map(({ user, pass, label, sub, avatar, color, bg }, i, arr) => (
                    <div
                      key={user}
                      className={`account-row flex items-center justify-between px-6 py-5 ${i < arr.length - 1 ? 'border-b border-white/5' : ''}`}
                      onClick={() => fillDemo(user, pass)}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-9 h-9 rounded-full ${bg} flex items-center justify-center ${color} font-bold text-sm`}>
                          {avatar}
                        </div>
                        <div>
                          <p className="text-sm font-medium">{label}</p>
                          <p className="text-xs text-slate-500">{sub}</p>
                        </div>
                      </div>
                      <div className="text-slate-400 text-sm">{user} / {pass}</div>
                    </div>
                  ))}
                </div>

                <p className="text-center text-slate-600 text-sm mt-5">
                  Click a row to auto-fill credentials
                </p>
              </div>

            </div>
          </div>

        </div>
      </div>
    </>
  )
}
