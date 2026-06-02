import { useState, useEffect } from 'react'
import {
  Camera, Monitor, Bell, Server, Play, RefreshCw, Download,
  Eye, AlertTriangle, UserPlus, Settings, FilmIcon,
  HardDrive, Cpu, Database, Wifi, CircleDot, Clock,
} from 'lucide-react'
import { discoveryApi, devicesApi } from '../api'

// ─── Editable static data (edit these manually as needed) ─────────────────────

const STORAGE_USED_TB   = 134.8
const STORAGE_TOTAL_TB  = 200
const CPU_USAGE_PCT     = 34
const NET_IN_MBPS       = 72
const NET_OUT_MBPS      = 48
const ACTIVE_ALERTS     = 5
const CRITICAL_ALERTS   = 2
const WARNING_ALERTS    = 3

const RECENT_ALERTS = [
  { id:1, msg:'Camera offline detected',   detail:'Corridor - KZL-01',         time:'2m ago',  color:'text-red-400'    },
  { id:2, msg:'Low storage warning',       detail:'NVR DS-7832NXI-K2',         time:'15m ago', color:'text-amber-400'  },
  { id:3, msg:'Motion detected',           detail:'Parking Area - KZL-01',     time:'32m ago', color:'text-blue-400'   },
  { id:4, msg:'Stream interrupted',        detail:'Garden Camera',             time:'1h ago',  color:'text-amber-400'  },
  { id:5, msg:'New device connected',      detail:'MPH-01 - DS-7832NXI-Q1',   time:'2h ago',  color:'text-emerald-400'},
]

const RECENT_ACTIVITY = [
  { id:1, Icon:UserPlus,  msg:'Admin logged in',       detail:'From 192.168.1.10',         time:'5m ago'  },
  { id:2, Icon:Camera,    msg:'Camera added',           detail:'Pantry - Camera 7',         time:'22m ago' },
  { id:3, Icon:Settings,  msg:'Settings updated',       detail:'Stream quality changed',    time:'1h ago'  },
  { id:4, Icon:FilmIcon,  msg:'Recording exported',     detail:'Lobby - Camera 3',          time:'2h ago'  },
  { id:5, Icon:UserPlus,  msg:'User created',           detail:'operator@samator.id',       time:'3h ago'  },
]

const SYSTEM_HEALTH = [
  { label:'CPU Usage',  Icon:Cpu,      value:`${CPU_USAGE_PCT}%`,             ok: CPU_USAGE_PCT < 80 },
  { label:'Database',   Icon:Database, value:'Running',                        ok: true               },
  { label:'Storage',    Icon:HardDrive,value:`${Math.round(STORAGE_USED_TB / STORAGE_TOTAL_TB * 100)}% used`, ok: (STORAGE_USED_TB / STORAGE_TOTAL_TB) < 0.85 },
  { label:'Network',    Icon:Wifi,     value:`${NET_IN_MBPS}/${NET_OUT_MBPS} Mbps`, ok: true          },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function nowStr() {
  return new Date().toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function DonutChart({ online, offline }) {
  const total = online + offline || 1
  const r = 44, cx = 54, cy = 54, c = 2 * Math.PI * r
  const onF = online / total

  return (
    <svg viewBox="0 0 108 108" width={100} height={100}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--secondary)" strokeWidth={12} />
      <circle cx={cx} cy={cy} r={r} fill="none"
        stroke="#10b981" strokeWidth={12}
        strokeDasharray={`${onF * c} ${c - onF * c}`}
        strokeDashoffset={0}
        transform={`rotate(-90,${cx},${cy})`}
      />
      {offline > 0 && (
        <circle cx={cx} cy={cy} r={r} fill="none"
          stroke="#ef4444" strokeWidth={12}
          strokeDasharray={`${(1 - onF) * c} ${onF * c}`}
          strokeDashoffset={-(onF * c)}
          transform={`rotate(-90,${cx},${cy})`}
        />
      )}
      <text x={cx} y={cy}   textAnchor="middle" dominantBaseline="middle" fill="var(--foreground)"       fontSize="18" fontWeight="700">{total}</text>
      <text x={cx} y={cy + 14} textAnchor="middle" dominantBaseline="middle" fill="var(--muted-foreground)" fontSize="8">Total</text>
    </svg>
  )
}

// ─── NVR Overview (replaces chart - shows real NVR status) ────────────────────

function NvrOverview({ nvrs, loading }) {
  const online  = nvrs.filter(n => n.sync_status === 'synced').length
  const offline = nvrs.length - online

  const sparkData = nvrs.slice(0, 12).map((n, i) => ({
    label: n.code || `NVR ${i + 1}`,
    ok: n.sync_status === 'synced',
  }))

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex items-center gap-6 mb-3">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
          <span className="text-[11px] text-muted-foreground">Online NVRs: <span className="text-emerald-400 font-semibold">{loading ? '—' : online}</span></span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-400 flex-shrink-0" />
          <span className="text-[11px] text-muted-foreground">Offline NVRs: <span className="text-red-400 font-semibold">{loading ? '—' : offline}</span></span>
        </div>
        <div className="ml-auto text-[10px] text-muted-foreground">{nvrs.length} total NVRs</div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">Loading…</div>
      ) : nvrs.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">No NVRs found</div>
      ) : (
        <div className="flex flex-wrap gap-1.5 content-start">
          {nvrs.map((nvr) => {
            const isOnline = nvr.sync_status === 'synced'
            return (
              <div
                key={nvr.id}
                title={`${nvr.branch_name || nvr.code} — ${nvr.nvr_ip || ''}`}
                className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium border ${
                  isOnline
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/10 border-red-500/20 text-red-400'
                }`}
              >
                <Monitor size={9} className="flex-shrink-0" />
                <span className="max-w-[90px] truncate">{nvr.branch_name || nvr.code || nvr.id.slice(0, 8)}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Dashboard View ───────────────────────────────────────────────────────────

export default function DashboardView() {
  const [nvrs,      setNvrs]      = useState([])
  const [cameras,   setCameras]   = useState([])
  const [devices,   setDevices]   = useState([])
  const [loading,   setLoading]   = useState(true)
  const [now,       setNow]       = useState(nowStr())

  useEffect(() => { load() }, [])

  // Tick clock every minute
  useEffect(() => {
    const t = setInterval(() => setNow(nowStr()), 60_000)
    return () => clearInterval(t)
  }, [])

  async function load() {
    setLoading(true)
    try {
      const [nvrList, devResult] = await Promise.allSettled([
        discoveryApi.getNvrs(),
        devicesApi.list(),
      ])

      const nvrs = nvrList.status === 'fulfilled' ? (nvrList.value || []) : []
      setNvrs(nvrs)

      const devs = devResult.status === 'fulfilled' ? (devResult.value?.items || []) : []
      setDevices(devs)

      const channelResults = await Promise.allSettled(
        nvrs.map(nvr => discoveryApi.getChannels(nvr.id))
      )
      const all = []
      nvrs.forEach((nvr, i) => {
        if (channelResults[i].status !== 'fulfilled') return
        const chs = channelResults[i].value?.channels || []
        chs.forEach(ch => all.push({
          id:       ch.id,
          isOnline: nvr.sync_status === 'synced' && ch.is_enabled === true,
          isEnabled: ch.is_enabled === true,
        }))
      })
      setCameras(all)
    } catch {}
    finally { setLoading(false) }
  }

  const totalCams    = cameras.filter(c => c.isEnabled).length
  const onlineCams   = cameras.filter(c => c.isOnline).length
  const offlineCams  = cameras.filter(c => c.isEnabled && !c.isOnline).length
  const camPct       = totalCams ? Math.round(onlineCams / totalCams * 100) : 0

  const onlineNvrs   = nvrs.filter(n => n.sync_status === 'synced').length
  const offlineNvrs  = nvrs.length - onlineNvrs

  const totalDevs   = devices.length
  const onlineDevs  = devices.filter(d => d.status === 'ONLINE').length
  const offlineDevs = devices.filter(d => d.status === 'OFFLINE').length

  const storagePct  = Math.round(STORAGE_USED_TB / STORAGE_TOTAL_TB * 100)

  const statCards = [
    {
      label: 'Synced Cameras',
      value: loading ? '—' : String(totalCams),
      Icon:  Camera,
      color: 'text-blue-400',
      bg:    'bg-blue-500/10 border-blue-500/20',
      sub:   <span className="text-[10px] text-muted-foreground">
        Enabled <span className="text-emerald-400 font-medium">{loading ? '—' : onlineCams}</span>
        {offlineCams > 0 && <> &bull; Disabled <span className="text-red-400 font-medium">{offlineCams}</span></>}
        {!loading && offlineNvrs > 0 && <> &bull; <span className="text-amber-400 font-medium">{offlineNvrs} NVRs unreachable</span></>}
      </span>,
    },
    {
      label: 'NVR-Confirmed Online',
      value: loading ? '—' : String(onlineCams),
      Icon:  CircleDot,
      color: 'text-emerald-400',
      bg:    'bg-emerald-500/10 border-emerald-500/20',
      sub:   <span className="text-[10px] text-muted-foreground">
        <span className="text-emerald-400 font-medium">{loading ? '—' : `${camPct}%`}</span> of synced fleet
        &nbsp;&bull; verify streams in Monitoring
      </span>,
    },
    {
      label: 'Total Devices',
      value: loading ? '—' : String(totalDevs),
      Icon:  Server,
      color: 'text-violet-400',
      bg:    'bg-violet-500/10 border-violet-500/20',
      sub:   <span className="text-[10px] text-muted-foreground">Online <span className="text-emerald-400 font-medium">{loading ? '—' : onlineDevs}</span> &bull; Offline <span className="text-red-400 font-medium">{loading ? '—' : offlineDevs}</span></span>,
    },
    {
      label: 'Active Alerts',
      value: String(ACTIVE_ALERTS),
      Icon:  AlertTriangle,
      color: 'text-amber-400',
      bg:    'bg-amber-500/10 border-amber-500/20',
      sub:   <span className="text-[10px] text-muted-foreground"><span className="text-red-400 font-medium">{CRITICAL_ALERTS}</span> critical &bull; <span className="text-amber-400 font-medium">{WARNING_ALERTS}</span> warnings</span>,
    },
    {
      label: 'Storage Used',
      value: String(STORAGE_USED_TB),
      Icon:  HardDrive,
      color: 'text-sky-400',
      bg:    'bg-sky-500/10 border-sky-500/20',
      sub:   (
        <div className="w-full mt-1">
          <div className="flex justify-between text-[10px] text-muted-foreground mb-0.5">
            <span>{STORAGE_USED_TB} TB</span><span>{STORAGE_TOTAL_TB} TB</span>
          </div>
          <div className="w-full h-1 bg-secondary rounded-full overflow-hidden">
            <div className="h-full bg-sky-400 rounded-full" style={{ width: `${storagePct}%` }} />
          </div>
        </div>
      ),
    },
  ]

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-background">

      {/* Greeting */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-base font-semibold text-foreground">{greeting()}, Admin 👋</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {loading
              ? 'Loading system status…'
              : `${onlineCams} cameras confirmed across ${onlineNvrs} reachable NVRs.${offlineNvrs > 0 ? ` ${offlineNvrs} NVRs unreachable — camera count unknown.` : ''}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock size={12} />
            <span>{now}</span>
          </div>
          <button
            onClick={load}
            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-5 gap-3">
        {statCards.map((card) => (
          <div key={card.label} className={`rounded-lg border p-3.5 flex flex-col gap-1.5 bg-card ${card.bg}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground font-medium">{card.label}</span>
              <div className={`w-7 h-7 rounded flex items-center justify-center ${card.bg}`}>
                <card.Icon size={14} className={card.color} />
              </div>
            </div>
            <p className={`text-2xl font-bold tracking-tight ${card.color}`}>
              {card.value}{card.label === 'Storage Used' ? ' TB' : ''}
            </p>
            {card.sub}
          </div>
        ))}
      </div>

      {/* Middle Row */}
      <div className="grid grid-cols-12 gap-3">
        {/* NVR Overview (real data) */}
        <div className="col-span-7 bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-xs font-semibold text-foreground">NVR Overview</h3>
              <p className="text-[10px] text-muted-foreground">Live sync status per NVR</p>
            </div>
            <button onClick={load} className="text-[10px] text-muted-foreground hover:text-foreground border border-border rounded px-2 py-0.5 flex items-center gap-1">
              <RefreshCw size={9} /> Refresh
            </button>
          </div>
          <div className="w-full" style={{ minHeight: 120 }}>
            <NvrOverview nvrs={nvrs} loading={loading} />
          </div>
        </div>

        {/* Camera Status Donut (real data) */}
        <div className="col-span-2 bg-card border border-border rounded-lg p-4 flex flex-col">
          <h3 className="text-xs font-semibold text-foreground mb-2">Camera Status</h3>
          <div className="flex-1 flex flex-col items-center justify-center gap-2">
            <DonutChart online={onlineCams} offline={offlineCams + offlineNvrs} />
            <div className="space-y-1 w-full">
              {[
                { label: 'Confirmed', count: onlineCams,             color: '#10b981' },
                { label: 'Disabled',  count: offlineCams,            color: '#ef4444' },
                { label: 'NVR down',  count: offlineNvrs,            color: '#f59e0b' },
              ].map(({ label, count, color }) => (
                <div key={label} className="flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                    <span className="text-muted-foreground">{label}</span>
                  </div>
                  <span className="text-foreground font-medium">{loading ? '—' : count}</span>
                </div>
              ))}
            </div>
            <p className="text-[9px] text-muted-foreground text-center leading-tight opacity-70">
              Stream-verified status available in Monitoring
            </p>
          </div>
        </div>

        {/* Recent Alerts (static — edit RECENT_ALERTS above) */}
        <div className="col-span-3 bg-card border border-border rounded-lg p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-foreground">Recent Alerts</h3>
            <button className="text-[10px] text-muted-foreground hover:text-foreground">View All</button>
          </div>
          <div className="flex-1 space-y-2.5 overflow-y-auto">
            {RECENT_ALERTS.map((alert) => (
              <div key={alert.id} className="flex items-start gap-2">
                <AlertTriangle size={12} className={`${alert.color} flex-shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-foreground leading-tight truncate">{alert.msg}</p>
                  <p className="text-[10px] text-muted-foreground truncate">{alert.detail}</p>
                </div>
                <span className="text-[9px] text-muted-foreground whitespace-nowrap flex-shrink-0">{alert.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-12 gap-3">
        {/* Recent Activity (static — edit RECENT_ACTIVITY above) */}
        <div className="col-span-5 bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-foreground">Recent Activity</h3>
            <button className="text-[10px] text-muted-foreground hover:text-foreground">View All</button>
          </div>
          <div className="space-y-3">
            {RECENT_ACTIVITY.map(({ id, Icon, msg, detail, time }) => (
              <div key={id} className="flex items-start gap-2.5">
                <div className="w-6 h-6 rounded bg-secondary flex items-center justify-center flex-shrink-0">
                  <Icon size={11} className="text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-foreground font-medium leading-tight">{msg}</p>
                  <p className="text-[10px] text-muted-foreground">{detail}</p>
                </div>
                <span className="text-[9px] text-muted-foreground whitespace-nowrap">{time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* System Health (static — edit SYSTEM_HEALTH above) */}
        <div className="col-span-4 bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-foreground">System Health</h3>
          </div>
          <div className="space-y-2.5">
            {SYSTEM_HEALTH.map(({ label, Icon, value, ok }) => (
              <div key={label} className="flex items-center gap-2.5">
                <div className={`w-6 h-6 rounded flex items-center justify-center flex-shrink-0 ${ok ? 'bg-emerald-500/15' : 'bg-amber-500/15'}`}>
                  <Icon size={12} className={ok ? 'text-emerald-400' : 'text-amber-400'} />
                </div>
                <span className="text-[11px] text-foreground flex-1">{label}</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${ok ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'}`}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="col-span-3 bg-card border border-border rounded-lg p-4">
          <h3 className="text-xs font-semibold text-foreground mb-3">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { Icon:Eye,      label:'Live View',   color:'text-blue-400',    bg:'bg-blue-500/10 hover:bg-blue-500/20 border-blue-500/20'      },
              { Icon:Play,     label:'Playback',    color:'text-violet-400',  bg:'bg-violet-500/10 hover:bg-violet-500/20 border-violet-500/20' },
              { Icon:Camera,   label:'Add Camera',  color:'text-emerald-400', bg:'bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/20' },
              { Icon:Download, label:'Export',      color:'text-amber-400',   bg:'bg-amber-500/10 hover:bg-amber-500/20 border-amber-500/20'    },
            ].map(({ Icon, label, color, bg }) => (
              <button key={label} className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-colors ${bg}`}>
                <Icon size={16} className={color} />
                <span className="text-[10px] text-foreground font-medium">{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

    </div>
  )
}
