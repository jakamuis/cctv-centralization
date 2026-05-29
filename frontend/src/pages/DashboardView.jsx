import { useState, useEffect } from 'react'
import {
  Camera, Monitor, Bell, Database,
  Activity, Maximize2, RefreshCw, AlertCircle, Server,
} from 'lucide-react'
import { discoveryApi } from '../api'

// ─── Mock data ────────────────────────────────────────────────────────────────

const RECENT_EVENTS = [
  { id:1, type:'Motion Detection',   camera:'CAM 03 - Office Floor 1', time:'10:24:31', color:'#ef4444' },
  { id:2, type:'Line Crossing',      camera:'CAM 11 - Front Gate',     time:'10:22:15', color:'#f59e0b' },
  { id:3, type:'Intrusion Detection',camera:'CAM 06 - Parking Area 1', time:'10:18:07', color:'#ef4444' },
  { id:4, type:'Camera Offline',     camera:'CAM 08 - Staircase 1',    time:'10:15:42', color:'#6b7280' },
  { id:5, type:'Motion Detection',   camera:'CAM 14 - Pantry',         time:'10:12:33', color:'#ef4444' },
]

const SYSTEM_STATUS = [
  { name:'VMS Server',       status:'Online',   color:'#22c55e' },
  { name:'Recording Server', status:'Online',   color:'#22c55e' },
  { name:'Storage Status',   status:'63% Used', color:'#f59e0b' },
  { name:'Network Status',   status:'Healthy',  color:'#22c55e' },
]

const CPU_DATA  = [20,25,22,28,30,25,22,20,28,32,35,30,25,28,22,20,25,28,30,28,25,22,28,30,28,25,22,28]
const NET_IN    = [40,45,50,48,55,60,58,52,48,55,65,70,68,60,55,58,62,68,72,70,65,60,65,70,72,68,65,72]
const NET_OUT   = [20,22,25,28,30,32,28,25,22,28,32,35,38,35,32,30,32,35,38,42,45,42,38,40,45,48,44,48]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sparkline(data, w, h) {
  const min = Math.min(...data), max = Math.max(...data), range = max - min || 1
  return 'M' + data.map((v, i) =>
    `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`
  ).join(' L')
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({ iconBg, Icon, title, value, sub, subColor = '#22c55e' }) {
  return (
    <div style={{
      background:'#141d2b', border:'1px solid rgba(255,255,255,0.07)',
      borderRadius:12, padding:'18px 20px',
      display:'flex', alignItems:'center', gap:16, flex:1,
    }}>
      <div style={{
        width:52, height:52, borderRadius:'50%', background:iconBg,
        display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
      }}>
        <Icon size={24} color="#fff" />
      </div>
      <div>
        <div style={{ fontSize:'.78rem', color:'#64748b', marginBottom:4 }}>{title}</div>
        <div style={{ fontSize:'2rem', fontWeight:700, color:'#fff', lineHeight:1 }}>{value}</div>
        <div style={{ fontSize:'.78rem', color:subColor, marginTop:5 }}>{sub}</div>
      </div>
    </div>
  )
}

function DonutChart({ online, offline, maintenance }) {
  const total = online + offline + maintenance || 1
  const r = 48, cx = 60, cy = 60, c = 2 * Math.PI * r

  const arc = (start, frac, color) => (
    <circle key={color}
      cx={cx} cy={cy} r={r} fill="none"
      stroke={color} strokeWidth={14}
      strokeDasharray={`${frac * c} ${c - frac * c}`}
      strokeDashoffset={-start * c}
      transform={`rotate(-90,${cx},${cy})`}
    />
  )

  const onF = online / total, offF = offline / total, mF = maintenance / total

  return (
    <svg viewBox="0 0 120 120" width={110} height={110}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e2a3b" strokeWidth={14} />
      {arc(0,         onF,  '#22c55e')}
      {arc(onF,       offF, '#ef4444')}
      {arc(onF+offF,  mF,   '#f59e0b')}
      <text x={cx} y={cy+1}  textAnchor="middle" dominantBaseline="middle" fill="#fff"    fontSize="20" fontWeight="700">{online + offline + maintenance}</text>
      <text x={cx} y={cy+16} textAnchor="middle" dominantBaseline="middle" fill="#64748b" fontSize="9">Total</text>
    </svg>
  )
}

function CameraTile({ camera }) {
  const online = camera?.isOnline
  return (
    <div style={{
      aspectRatio:'16/9', background:'#080e17',
      border:'1px solid rgba(255,255,255,0.05)',
      borderRadius:6, position:'relative', overflow:'hidden', cursor:'pointer',
    }}>
      {camera ? (
        <>
          <div style={{
            position:'absolute', top:0, left:0, right:0,
            padding:'5px 7px',
            background:'linear-gradient(to bottom,rgba(0,0,0,0.75),transparent)',
            display:'flex', alignItems:'center', justifyContent:'space-between', zIndex:2,
          }}>
            <span style={{ fontSize:'.63rem', color:'#e2e8f0', fontWeight:500 }}>
              {camera.name}
            </span>
            <span style={{
              width:6, height:6, borderRadius:'50%',
              background: online ? '#22c55e' : '#ef4444',
              boxShadow: online ? '0 0 4px #22c55e' : 'none',
            }} />
          </div>
          <div style={{
            position:'absolute', inset:0,
            display:'flex', alignItems:'center', justifyContent:'center',
            opacity: online ? 0.12 : 0.04,
          }}>
            <Camera size={26} color="#94a3b8" />
          </div>
        </>
      ) : (
        <div style={{
          position:'absolute', inset:0,
          display:'flex', alignItems:'center', justifyContent:'center',
        }}>
          <Camera size={14} color="#1e2a3b" />
        </div>
      )}
    </div>
  )
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function DashboardView() {
  const [nvrs,    setNvrs]    = useState([])
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)
  const [grid,    setGrid]    = useState(16)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const nvrList = await discoveryApi.getNvrs()
      setNvrs(nvrList)
      const results = await Promise.allSettled(
        nvrList.map(nvr => discoveryApi.getChannels(nvr.id))
      )
      const all = []
      nvrList.forEach((nvr, i) => {
        if (results[i].status !== 'fulfilled') return
        const chs = results[i].value?.channels || []
        chs.forEach(ch => all.push({
          id:        ch.id,
          name:      ch.channel_name || `Channel ${ch.channel_id}`,
          nvrCode:   nvr.code,
          isEnabled: ch.is_enabled === true,
          isOnline:  nvr.sync_status === 'synced' && ch.is_enabled === true,
        }))
      })
      setCameras(all)
    } catch {}
    finally { setLoading(false) }
  }

  const totalCams   = cameras.filter(c => c.isEnabled).length
  const onlineCams  = cameras.filter(c => c.isOnline).length
  const offlineCams = cameras.filter(c => c.isEnabled && !c.isOnline).length
  const pct         = totalCams ? Math.round(onlineCams / totalCams * 100) : 0

  const cols    = grid === 4 ? 2 : grid === 9 ? 3 : 4
  const gridCams = cameras.slice(0, grid)
  const padded  = [...gridCams, ...Array(Math.max(0, grid - gridCams.length)).fill(null)]

  const card = (style = {}) => ({
    background:'#141d2b',
    border:'1px solid rgba(255,255,255,0.07)',
    borderRadius:12,
    ...style,
  })

  const hdr = { display:'flex', alignItems:'center', justifyContent:'space-between', padding:'12px 16px', borderBottom:'1px solid rgba(255,255,255,0.07)' }
  const viewAll = { background:'none', border:'none', color:'#3b82f6', fontSize:'.78rem', cursor:'pointer' }

  return (
    <div style={{
      flex:1, overflow:'auto', background:'#0d1117',
      padding:18, display:'flex', flexDirection:'column', gap:14,
      fontFamily:"'Inter',sans-serif",
    }}>

      {/* ── Stat cards ── */}
      <div style={{ display:'flex', gap:14 }}>
        <StatCard iconBg="rgba(59,130,246,0.22)"  Icon={Camera}   title="Total Cameras"   value={loading?'—':totalCams}  sub={loading?'':  `Online ${onlineCams}`} />
        <StatCard iconBg="rgba(34,197,94,0.22)"   Icon={Monitor}  title="Online Cameras"  value={loading?'—':onlineCams} sub={loading?'':  `${pct}%`} />
        <StatCard iconBg="rgba(139,92,246,0.22)"  Icon={Bell}     title="Active Events"   value="12"                     sub="View all"          subColor="#3b82f6" />
        <StatCard iconBg="rgba(245,158,11,0.22)"  Icon={Database} title="Total Storage"   value="45.2 TB"                sub="63% Used"          subColor="#f59e0b" />
      </div>

      {/* ── Middle row: Live View + Recent Events ── */}
      <div style={{ display:'flex', gap:14, minHeight:380 }}>

        {/* Live View */}
        <div style={{ ...card(), flex:1, display:'flex', flexDirection:'column', overflow:'hidden', minWidth:0 }}>
          <div style={hdr}>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <span style={{ width:8, height:8, borderRadius:'50%', background:'#22c55e', boxShadow:'0 0 6px #22c55e' }} />
              <span style={{ fontSize:'.9rem', fontWeight:600, color:'#e2e8f0' }}>Live View</span>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              {[{ n:4, label:'2×2' }, { n:9, label:'3×3' }, { n:16, label:'4×4' }].map(({ n, label }) => (
                <button key={n} onClick={() => setGrid(n)} style={{
                  padding:'3px 9px', borderRadius:6, cursor:'pointer',
                  background: grid===n ? 'rgba(59,130,246,0.2)' : 'transparent',
                  border:`1px solid ${grid===n ? '#3b82f6' : 'rgba(255,255,255,0.1)'}`,
                  color: grid===n ? '#3b82f6' : '#64748b', fontSize:'.73rem',
                }}>
                  {label}
                </button>
              ))}
              <button style={{ padding:'3px 9px', borderRadius:6, background:'transparent', border:'1px solid rgba(255,255,255,0.1)', color:'#64748b', fontSize:'.73rem', cursor:'pointer' }}>
                {grid} Screens ▾
              </button>
              <button style={{ padding:5, borderRadius:6, background:'transparent', border:'1px solid rgba(255,255,255,0.1)', color:'#64748b', cursor:'pointer', display:'flex' }}>
                <Maximize2 size={14} />
              </button>
            </div>
          </div>

          <div style={{
            flex:1, padding:10, overflow:'hidden',
            display:'grid', gridTemplateColumns:`repeat(${cols},1fr)`, gap:6,
          }}>
            {padded.map((cam, i) => <CameraTile key={i} camera={cam} />)}
          </div>

          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'8px 16px', borderTop:'1px solid rgba(255,255,255,0.07)' }}>
            <div style={{ display:'flex', alignItems:'center', gap:6 }}>
              <span style={{ width:8, height:8, borderRadius:'50%', background:'#3b82f6' }} />
              <span style={{ fontSize:'.78rem', color:'#64748b' }}>Live</span>
            </div>
            <div style={{ display:'flex', gap:2 }}>
              {[Camera, Activity, Maximize2, RefreshCw].map((Icon, i) => (
                <button key={i} style={{ padding:6, borderRadius:6, background:'transparent', border:'none', color:'#64748b', cursor:'pointer' }}>
                  <Icon size={14} />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Events + System Status */}
        <div style={{ ...card(), width:280, display:'flex', flexDirection:'column', overflow:'hidden', flexShrink:0 }}>
          <div style={hdr}>
            <span style={{ fontSize:'.9rem', fontWeight:600, color:'#e2e8f0' }}>Recent Events</span>
            <button style={viewAll}>View all</button>
          </div>

          <div style={{ flex:1, overflow:'auto' }}>
            {RECENT_EVENTS.map(ev => (
              <div key={ev.id} style={{ display:'flex', alignItems:'flex-start', gap:10, padding:'11px 14px', borderBottom:'1px solid rgba(255,255,255,0.04)', cursor:'pointer' }}
                   onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,0.03)'}
                   onMouseLeave={e => e.currentTarget.style.background='transparent'}>
                <div style={{ width:30, height:30, borderRadius:'50%', background:`${ev.color}22`, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, marginTop:2 }}>
                  <AlertCircle size={13} color={ev.color} />
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ fontSize:'.82rem', fontWeight:600, color:'#e2e8f0' }}>{ev.type}</div>
                  <div style={{ fontSize:'.73rem', color:'#64748b', marginTop:2 }}>{ev.camera}</div>
                  <div style={{ fontSize:'.7rem',  color:'#3d5a80', marginTop:2 }}>{ev.time}</div>
                </div>
                <div style={{ width:50, height:34, borderRadius:4, background:'#0a0f18', border:'1px solid rgba(255,255,255,0.05)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                  <Camera size={12} color="#1e2a3b" />
                </div>
              </div>
            ))}

            {/* System Status */}
            <div style={{ padding:'12px 14px 8px', borderTop:'1px solid rgba(255,255,255,0.07)' }}>
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:10 }}>
                <span style={{ fontSize:'.9rem', fontWeight:600, color:'#e2e8f0' }}>System Status</span>
                <button style={viewAll}>View all</button>
              </div>
              {SYSTEM_STATUS.map(s => (
                <div key={s.name} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'7px 0', borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:7 }}>
                    <Server size={12} color="#64748b" />
                    <span style={{ fontSize:'.78rem', color:'#94a3b8' }}>{s.name}</span>
                  </div>
                  <span style={{ fontSize:'.75rem', fontWeight:600, color:s.color }}>{s.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom row ── */}
      <div style={{ display:'flex', gap:14 }}>

        {/* Device Status */}
        <div style={{ ...card({ padding:16 }), flex:1 }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14 }}>
            <span style={{ fontSize:'.9rem', fontWeight:600, color:'#e2e8f0' }}>Device Status</span>
            <button style={viewAll}>View all</button>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:20 }}>
            <DonutChart online={onlineCams} offline={offlineCams} maintenance={0} />
            <div style={{ flex:1, display:'flex', flexDirection:'column', gap:10 }}>
              {[
                { label:'Online',      count:onlineCams,  color:'#22c55e' },
                { label:'Offline',     count:offlineCams, color:'#ef4444' },
                { label:'Maintenance', count:0,           color:'#f59e0b' },
              ].map(({ label, count, color }) => (
                <div key={label} style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                    <span style={{ width:8, height:8, borderRadius:'50%', background:color, display:'inline-block' }} />
                    <span style={{ fontSize:'.8rem', color:'#94a3b8' }}>{label}</span>
                  </div>
                  <span style={{ fontSize:'.8rem', color:'#e2e8f0', fontWeight:600 }}>
                    {loading ? '—' : count}&nbsp;
                    <span style={{ color:'#64748b', fontWeight:400 }}>
                      ({loading || !totalCams ? '—' : `${Math.round(count/totalCams*100)}%`})
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Storage Overview */}
        <div style={{ ...card({ padding:16 }), flex:1 }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14 }}>
            <span style={{ fontSize:'.9rem', fontWeight:600, color:'#e2e8f0' }}>Storage Overview</span>
            <button style={viewAll}>View all</button>
          </div>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:10 }}>
            <span style={{ fontSize:'.83rem', color:'#94a3b8' }}>45.2 TB / 72 TB Used</span>
            <span style={{ fontSize:'.83rem', fontWeight:600, color:'#e2e8f0' }}>63%</span>
          </div>
          <div style={{ display:'flex', height:8, borderRadius:4, overflow:'hidden', background:'#0f1c2e', marginBottom:14 }}>
            <div style={{ width:'45%', background:'#3b82f6' }} />
            <div style={{ width:'17%', background:'#8b5cf6' }} />
          </div>
          <div style={{ display:'flex', gap:14 }}>
            {[
              { label:'Recording', value:'32.6 TB', color:'#3b82f6' },
              { label:'Archive',   value:'8.4 TB',  color:'#8b5cf6' },
              { label:'Free',      value:'26.8 TB', color:'#3d5a80' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ flex:1 }}>
                <div style={{ display:'flex', alignItems:'center', gap:4, marginBottom:3 }}>
                  <span style={{ width:8, height:8, borderRadius:2, background:color, display:'inline-block' }} />
                  <span style={{ fontSize:'.7rem', color:'#64748b' }}>{label}</span>
                </div>
                <span style={{ fontSize:'.8rem', fontWeight:600, color:'#e2e8f0' }}>{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CPU & Network */}
        <div style={{ ...card({ padding:16 }), flex:1, display:'flex', flexDirection:'column' }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:10 }}>
            <span style={{ fontSize:'.9rem', fontWeight:600, color:'#e2e8f0' }}>CPU & Network</span>
            <button style={{ padding:'3px 8px', borderRadius:6, background:'transparent', border:'1px solid rgba(255,255,255,0.1)', color:'#64748b', fontSize:'.73rem', cursor:'pointer' }}>
              Today ▾
            </button>
          </div>
          <div style={{ display:'flex', gap:20, marginBottom:10 }}>
            <div>
              <div style={{ fontSize:'.7rem', color:'#64748b' }}>CPU Usage</div>
              <div style={{ fontSize:'1.5rem', fontWeight:700, color:'#fff' }}>28%</div>
            </div>
            <div>
              <div style={{ fontSize:'.7rem', color:'#64748b' }}>Network (In/Out)</div>
              <div style={{ fontSize:'.95rem', fontWeight:700, color:'#fff', marginTop:4 }}>72 Mbps / 48 Mbps</div>
            </div>
          </div>
          <svg width="100%" height="64" viewBox="0 0 300 64" preserveAspectRatio="none" style={{ flex:1 }}>
            <path d={sparkline(CPU_DATA,  300, 64)} fill="none" stroke="#3b82f6" strokeWidth="1.5" />
            <path d={sparkline(NET_IN,    300, 64)} fill="none" stroke="#22c55e" strokeWidth="1.5" />
            <path d={sparkline(NET_OUT,   300, 64)} fill="none" stroke="#f59e0b" strokeWidth="1.5" />
          </svg>
          <div style={{ display:'flex', gap:14, marginTop:8 }}>
            {[
              { label:'CPU',         color:'#3b82f6' },
              { label:'Network In',  color:'#22c55e' },
              { label:'Network Out', color:'#f59e0b' },
            ].map(({ label, color }) => (
              <div key={label} style={{ display:'flex', alignItems:'center', gap:4 }}>
                <span style={{ width:16, height:2, background:color, display:'inline-block', borderRadius:1 }} />
                <span style={{ fontSize:'.7rem', color:'#64748b' }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  )
}
