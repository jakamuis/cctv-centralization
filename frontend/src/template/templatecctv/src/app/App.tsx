import { useState } from "react";
import {
  LayoutDashboard,
  Monitor,
  Camera,
  Play,
  CalendarDays,
  BarChart2,
  Settings,
  ChevronRight,
  ChevronDown,
  Search,
  Bell,
  RefreshCw,
  Maximize2,
  Video,
  Server,
  Plus,
  Filter,
  SortAsc,
  Minimize2,
  ZoomIn,
  ZoomOut,
  Ratio,
  CircleDot,
  Info,
  Activity,
  Clock,
  HardDrive,
  AlertTriangle,
  Users,
  Map,
  ShieldCheck,
  FileText,
  ChevronLeft,
  Cpu,
  Database,
  Wifi,
  Download,
  Eye,
  UserPlus,
  FilmIcon,
} from "lucide-react";
// Removed Recharts imports — analytics charts replaced with monitoring UI

// ─── Types ────────────────────────────────────────────────────────────────────

type CameraStatus = "online" | "offline";
type ActiveNav = string;
type ActiveTab = "overview" | "information" | "stream" | "events";

interface CameraItem {
  id: string;
  name: string;
  status: CameraStatus;
  channel: number;
  model: string;
  ip: string;
  lastSeen: string;
  nvrId: string;
  nvrName: string;
  siteId: string;
  siteName: string;
}

interface NVRItem {
  id: string;
  name: string;
  status: CameraStatus;
  cameras: CameraItem[];
}

interface SiteItem {
  id: string;
  name: string;
  nvrs: NVRItem[];
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const sites: SiteItem[] = [
  {
    id: "kzl-01",
    name: "KZL-01",
    nvrs: [
      {
        id: "ds-7832nxi-k2",
        name: "DS-7832NXI-K2",
        status: "online",
        cameras: [
          { id: "c1", name: "Parking Area", status: "online", channel: 1, model: "IPC-B4", ip: "10.10.10.44", lastSeen: "23 May 2025 10:35:40", nvrId: "ds-7832nxi-k2", nvrName: "DS-7832NXI-K2", siteId: "kzl-01", siteName: "KZL-01" },
          { id: "c2", name: "Office", status: "online", channel: 2, model: "IPC-B4", ip: "10.10.10.45", lastSeen: "23 May 2025 10:35:40", nvrId: "ds-7832nxi-k2", nvrName: "DS-7832NXI-K2", siteId: "kzl-01", siteName: "KZL-01" },
          { id: "c3", name: "Lobby", status: "online", channel: 3, model: "IPC-B4", ip: "10.10.10.46", lastSeen: "23 May 2025 10:35:40", nvrId: "ds-7832nxi-k2", nvrName: "DS-7832NXI-K2", siteId: "kzl-01", siteName: "KZL-01" },
          { id: "c4", name: "Corridor", status: "offline", channel: 4, model: "IPC-B4", ip: "10.10.10.47", lastSeen: "22 May 2025 08:12:05", nvrId: "ds-7832nxi-k2", nvrName: "DS-7832NXI-K2", siteId: "kzl-01", siteName: "KZL-01" },
          { id: "c5", name: "Garden", status: "online", channel: 5, model: "IPC-B4", ip: "10.10.10.48", lastSeen: "23 May 2025 10:35:40", nvrId: "ds-7832nxi-k2", nvrName: "DS-7832NXI-K2", siteId: "kzl-01", siteName: "KZL-01" },
          { id: "c6", name: "Restaurant", status: "online", channel: 6, model: "IPC-B4", ip: "10.10.10.49", lastSeen: "23 May 2025 10:35:40", nvrId: "ds-7832nxi-k2", nvrName: "DS-7832NXI-K2", siteId: "kzl-01", siteName: "KZL-01" },
        ],
      },
    ],
  },
  {
    id: "ds-7832nxi-q1",
    name: "DS-7832NXI-Q1",
    nvrs: [
      { id: "mph-01", name: "MPH-01", status: "online", cameras: [] },
      { id: "bks-02", name: "BKS-02", status: "online", cameras: [] },
      { id: "mpt-07", name: "MPT-07", status: "offline", cameras: [] },
    ],
  },
];

const systemOverviewData = [
  { time: "00:00", online: 92, offline: 28, critical: 3 },
  { time: "02:00", online: 90, offline: 30, critical: 4 },
  { time: "04:00", online: 88, offline: 32, critical: 5 },
  { time: "06:00", online: 94, offline: 26, critical: 3 },
  { time: "08:00", online: 98, offline: 22, critical: 2 },
  { time: "10:00", online: 101, offline: 19, critical: 2 },
  { time: "12:00", online: 105, offline: 17, critical: 1 },
  { time: "14:00", online: 103, offline: 19, critical: 2 },
  { time: "16:00", online: 99, offline: 21, critical: 3 },
  { time: "18:00", online: 97, offline: 23, critical: 4 },
  { time: "20:00", online: 95, offline: 25, critical: 3 },
  { time: "22:00", online: 98, offline: 22, critical: 2 },
];

const deviceStatusData = [
  { name: "Online", value: 98, color: "#10b981" },
  { name: "Offline", value: 20, color: "#ef4444" },
  { name: "Unknown", value: 10, color: "#f59e0b" },
];

const recentAlerts = [
  { id: 1, icon: AlertTriangle, msg: "Camera offline detected", detail: "Corridor - KZL-01", time: "2m ago", color: "text-red-400" },
  { id: 2, icon: AlertTriangle, msg: "Low storage warning", detail: "NVR DS-7832NXI-K2", time: "15m ago", color: "text-amber-400" },
  { id: 3, icon: AlertTriangle, msg: "Motion detected", detail: "Parking Area - KZL-01", time: "32m ago", color: "text-blue-400" },
  { id: 4, icon: AlertTriangle, msg: "Stream interrupted", detail: "Garden Camera", time: "1h ago", color: "text-amber-400" },
  { id: 5, icon: AlertTriangle, msg: "New device connected", detail: "MPH-01 - DS-7832NXI-Q1", time: "2h ago", color: "text-emerald-400" },
];

const recentActivity = [
  { id: 1, icon: UserPlus, msg: "Admin logged in", detail: "From 192.168.1.10", time: "5m ago" },
  { id: 2, icon: Camera, msg: "Camera added", detail: "Pantry - Camera 7", time: "22m ago" },
  { id: 3, icon: Users, msg: "User created", detail: "operator@samator.id", time: "1h ago" },
  { id: 4, icon: FilmIcon, msg: "Recording exported", detail: "Lobby - Camera 3", time: "2h ago" },
  { id: 5, icon: Settings, msg: "Settings updated", detail: "Stream quality changed", time: "3h ago" },
];

const systemHealth = [
  { label: "CPU", status: "Normal", ok: true },
  { label: "Database", status: "Running", ok: true },
  { label: "Storage", status: "Warning", ok: false },
  { label: "Network", status: "Running", ok: true },
];

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", section: "main" },
  { icon: Eye, label: "Live Streams", section: "main" },
  { icon: Monitor, label: "Live View", section: "main" },
  { icon: Play, label: "Playback", section: "main" },
  { icon: CalendarDays, label: "Events", section: "main" },
  { icon: Server, label: "Devices", section: "management" },
  { icon: Camera, label: "Camera Groups", section: "management" },
  { icon: Map, label: "Maps", section: "management" },
  { icon: Users, label: "Users", section: "management" },
  { icon: ShieldCheck, label: "Roles & Permissions", section: "management" },
  { icon: FileText, label: "Audit Logs", section: "management" },
  { icon: Settings, label: "Settings", section: "bottom" },
];

const siteNavItems = [
  { icon: LayoutDashboard, label: "Dashboard" },
  { icon: Monitor, label: "Sites", active: true },
  { icon: Server, label: "Devices" },
  { icon: Camera, label: "Cameras" },
  { icon: Play, label: "Playback" },
  { icon: CalendarDays, label: "Events" },
  { icon: BarChart2, label: "Reports" },
  { icon: Settings, label: "Settings" },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusDot({ status }: { status: CameraStatus }) {
  return (
    <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${status === "online" ? "bg-emerald-400" : "bg-red-500"}`} />
  );
}

function StatusBadge({ status }: { status: CameraStatus }) {
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${status === "online" ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
      {status === "online" ? "Online" : "Offline"}
    </span>
  );
}

// ─── Dashboard View ───────────────────────────────────────────────────────────

function DashboardView() {
  const statCards = [
    {
      label: "Total Cameras",
      value: "128",
      icon: Camera,
      color: "text-blue-400",
      bg: "bg-blue-500/10 border-blue-500/20",
      sub: <span className="text-[10px] text-muted-foreground">Online <span className="text-emerald-400 font-medium">98</span> &bull; Offline <span className="text-red-400 font-medium">30</span> (23%)</span>,
    },
    {
      label: "Online Cameras",
      value: "98",
      icon: CircleDot,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/20",
      sub: <span className="text-[10px] text-muted-foreground"><span className="text-emerald-400 font-medium">76.6%</span> of total fleet</span>,
    },
    {
      label: "Total Devices",
      value: "32",
      icon: Server,
      color: "text-violet-400",
      bg: "bg-violet-500/10 border-violet-500/20",
      sub: <span className="text-[10px] text-muted-foreground">Online <span className="text-emerald-400 font-medium">28</span> &bull; Offline <span className="text-red-400 font-medium">4</span></span>,
    },
    {
      label: "Active Alerts",
      value: "5",
      icon: AlertTriangle,
      color: "text-amber-400",
      bg: "bg-amber-500/10 border-amber-500/20",
      sub: <span className="text-[10px] text-muted-foreground"><span className="text-red-400 font-medium">2</span> critical &bull; <span className="text-amber-400 font-medium">3</span> warnings</span>,
    },
    {
      label: "Storage Used",
      value: "134.8",
      icon: HardDrive,
      color: "text-sky-400",
      bg: "bg-sky-500/10 border-sky-500/20",
      sub: (
        <div className="w-full mt-1">
          <div className="flex justify-between text-[10px] text-muted-foreground mb-0.5">
            <span>134.8 TB</span><span>200 TB</span>
          </div>
          <div className="w-full h-1 bg-secondary rounded-full overflow-hidden">
            <div className="h-full bg-sky-400 rounded-full" style={{ width: "67%" }} />
          </div>
        </div>
      ),
    },
  ];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-popover border border-border rounded p-2 text-[11px] shadow-xl">
        <p className="text-muted-foreground mb-1">{label}</p>
        {payload.map((p: any) => (
          <p key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</p>
        ))}
      </div>
    );
  };

  const RADIAN = Math.PI / 180;
  const renderCustomLabel = ({ cx, cy }: any) => (
    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" className="fill-foreground">
      <tspan x={cx} dy="-6" fontSize="22" fontWeight="600" fill="#e2e8f0">128</tspan>
      <tspan x={cx} dy="18" fontSize="11" fill="#64748b">Total</tspan>
    </text>
  );

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-background">
      {/* Greeting */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-base font-semibold text-foreground">Good morning, Admin 👋</h1>
          <p className="text-xs text-muted-foreground mt-0.5">All systems operational. No critical alerts today.</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock size={12} />
          <span>23 May 2025 &bull; 10:35 AM</span>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-5 gap-3">
        {statCards.map((card) => (
          <div key={card.label} className={`rounded-lg border p-3.5 flex flex-col gap-1.5 bg-card ${card.bg}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground font-medium">{card.label}</span>
              <div className={`w-7 h-7 rounded flex items-center justify-center ${card.bg}`}>
                <card.icon size={14} className={card.color} />
              </div>
            </div>
            <p className={`text-2xl font-bold tracking-tight ${card.color}`}>{card.value}{card.label === "Storage Used" ? " TB" : ""}</p>
            {card.sub}
          </div>
        ))}
      </div>

      {/* Middle Row */}
      <div className="grid grid-cols-12 gap-3">
        {/* System Overview Chart */}
        <div className="col-span-7 bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-xs font-semibold text-foreground">System Overview</h3>
              <p className="text-[10px] text-muted-foreground">Last 24 Hours</p>
            </div>
            <button className="text-[10px] text-muted-foreground hover:text-foreground border border-border rounded px-2 py-0.5">View All</button>
          </div>
          <div className="w-full h-40 rounded-md bg-muted/30 flex items-center justify-center">
            <span className="text-sm text-muted-foreground">System overview chart removed — monitoring-focused UI</span>
          </div>
        </div>

        {/* Device Status Donut */}
        <div className="col-span-2 bg-card border border-border rounded-lg p-4 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-foreground">Device Status</h3>
          </div>
          <div className="flex-1 flex flex-col items-center justify-center gap-2">
            <div className="flex items-center justify-center w-24 h-24 bg-muted/30 rounded-full">
              <span className="text-xs text-muted-foreground">Uptime</span>
            </div>
            <div className="space-y-1 mt-1 w-full">
              {deviceStatusData.map((d) => (
                <div key={d.name} className="flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: d.color }} />
                    <span className="text-muted-foreground">{d.name}</span>
                  </div>
                  <span className="text-foreground font-medium">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="col-span-3 bg-card border border-border rounded-lg p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-foreground">Recent Alerts</h3>
            <button className="text-[10px] text-muted-foreground hover:text-foreground">View All</button>
          </div>
          <div className="flex-1 space-y-2.5 overflow-y-auto">
            {recentAlerts.map((alert) => (
              <div key={alert.id} className="flex items-start gap-2">
                <alert.icon size={12} className={`${alert.color} flex-shrink-0 mt-0.5`} />
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
        {/* Recent Activity */}
        <div className="col-span-5 bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-foreground">Recent Activity</h3>
            <button className="text-[10px] text-muted-foreground hover:text-foreground">View All</button>
          </div>
          <div className="space-y-3">
            {recentActivity.map((act) => (
              <div key={act.id} className="flex items-start gap-2.5">
                <div className="w-6 h-6 rounded bg-secondary flex items-center justify-center flex-shrink-0">
                  <act.icon size={11} className="text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-foreground font-medium leading-tight">{act.msg}</p>
                  <p className="text-[10px] text-muted-foreground">{act.detail}</p>
                </div>
                <span className="text-[9px] text-muted-foreground whitespace-nowrap">{act.time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* System Health */}
        <div className="col-span-4 bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-foreground">System Health</h3>
            <button className="text-[10px] text-muted-foreground hover:text-foreground">View All</button>
          </div>
          <div className="space-y-2.5">
            {[
              { label: "CPU Usage", icon: Cpu, value: "34%", ok: true },
              { label: "Database", icon: Database, value: "Running", ok: true },
              { label: "Storage", icon: HardDrive, value: "67% used", ok: false },
              { label: "Network", icon: Wifi, value: "Normal", ok: true },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2.5">
                <div className={`w-6 h-6 rounded flex items-center justify-center flex-shrink-0 ${item.ok ? "bg-emerald-500/15" : "bg-amber-500/15"}`}>
                  <item.icon size={12} className={item.ok ? "text-emerald-400" : "text-amber-400"} />
                </div>
                <span className="text-[11px] text-foreground flex-1">{item.label}</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${item.ok ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"}`}>
                  {item.value}
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
              { icon: Eye, label: "Live View", color: "text-blue-400", bg: "bg-blue-500/10 hover:bg-blue-500/20 border-blue-500/20" },
              { icon: Play, label: "Playback", color: "text-violet-400", bg: "bg-violet-500/10 hover:bg-violet-500/20 border-violet-500/20" },
              { icon: Camera, label: "Add Camera", color: "text-emerald-400", bg: "bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/20" },
              { icon: Download, label: "Export", color: "text-amber-400", bg: "bg-amber-500/10 hover:bg-amber-500/20 border-amber-500/20" },
            ].map((action) => (
              <button
                key={action.label}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-colors ${action.bg}`}
              >
                <action.icon size={16} className={action.color} />
                <span className="text-[10px] text-foreground font-medium">{action.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Sites View ───────────────────────────────────────────────────────────────

function SitesView() {
  const [expandedSites, setExpandedSites] = useState<Set<string>>(new Set(["kzl-01", "ds-7832nxi-k2"]));
  const [selectedCamera, setSelectedCamera] = useState<CameraItem>(sites[0].nvrs[0].cameras[2]);
  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");
  const [streamLoaded, setStreamLoaded] = useState(false);
  const [siteSearch, setSiteSearch] = useState("");

  const toggleExpand = (id: string) => {
    setExpandedSites((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const infoRows = [
    { label: "Camera Name", value: selectedCamera.name },
    { label: "Channel", value: String(selectedCamera.channel) },
    { label: "NVR", value: selectedCamera.nvrName },
    { label: "Model", value: selectedCamera.model },
    { label: "IP Address", value: selectedCamera.ip },
    { label: "Last Seen", value: selectedCamera.lastSeen },
  ];

  const streamRows = [
    { label: "Protocol", value: "RTSP" },
    { label: "Stream Type", value: "Main Stream" },
    { label: "Resolution", value: "2560×1520 4MP" },
    { label: "FPS", value: "20" },
    { label: "Bitrate", value: "4098 kbps" },
  ];

  return (
    <>
      {/* Sites Explorer */}
      <aside className="w-56 flex flex-col border-r border-border bg-card flex-shrink-0">
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-border">
          <span className="text-xs font-semibold text-foreground">Sites Explorer</span>
          <div className="flex items-center gap-1">
            <button className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><Filter size={12} /></button>
            <button className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><SortAsc size={12} /></button>
          </div>
        </div>
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center gap-2 bg-[#1a2436] border border-border rounded px-2 py-1.5">
            <Search size={11} className="text-muted-foreground flex-shrink-0" />
            <input type="text" value={siteSearch} onChange={(e) => setSiteSearch(e.target.value)} placeholder="Search items, device..." className="bg-transparent text-[11px] text-foreground placeholder-muted-foreground outline-none w-full" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-1 text-[11px]">
          {sites.map((site) => (
            <div key={site.id}>
              <button onClick={() => toggleExpand(site.id)} className="w-full flex items-center gap-1.5 px-3 py-1.5 hover:bg-secondary/50 text-foreground">
                {expandedSites.has(site.id) ? <ChevronDown size={11} className="text-muted-foreground flex-shrink-0" /> : <ChevronRight size={11} className="text-muted-foreground flex-shrink-0" />}
                <Monitor size={11} className="text-muted-foreground flex-shrink-0" />
                <span className="flex-1 text-left truncate font-medium">{site.name}</span>
              </button>
              {expandedSites.has(site.id) && site.nvrs.map((nvr) => (
                <div key={nvr.id}>
                  <button onClick={() => toggleExpand(nvr.id)} className="w-full flex items-center gap-1.5 pl-7 pr-3 py-1.5 hover:bg-secondary/50 text-foreground">
                    {expandedSites.has(nvr.id) ? <ChevronDown size={11} className="text-muted-foreground flex-shrink-0" /> : <ChevronRight size={11} className="text-muted-foreground flex-shrink-0" />}
                    <Server size={11} className="text-muted-foreground flex-shrink-0" />
                    <span className="flex-1 text-left truncate">{nvr.name}</span>
                    <StatusBadge status={nvr.status} />
                  </button>
                  {expandedSites.has(nvr.id) && nvr.cameras.filter((cam) => siteSearch === "" || cam.name.toLowerCase().includes(siteSearch.toLowerCase())).map((cam) => (
                    <button key={cam.id} onClick={() => { setSelectedCamera(cam); setStreamLoaded(false); setActiveTab("overview"); }} className={`w-full flex items-center gap-1.5 pl-12 pr-3 py-1.5 ${selectedCamera.id === cam.id ? "bg-accent/40 text-primary" : "hover:bg-secondary/50 text-foreground"}`}>
                      <Camera size={10} className="flex-shrink-0" />
                      <span className="flex-1 text-left truncate">{cam.name}</span>
                      <StatusDot status={cam.status} />
                    </button>
                  ))}
                </div>
              ))}
            </div>
          ))}
          <button className="w-full flex items-center gap-1.5 px-3 py-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary/50 mt-1">
            <Plus size={11} /><span>Add Site</span>
          </button>
        </div>
      </aside>

      {/* Camera Details */}
      <main className="w-[360px] flex flex-col border-r border-border bg-background flex-shrink-0">
        <div className="px-4 pt-3 pb-0 flex-shrink-0">
          <div className="flex items-start justify-between mb-1">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded bg-primary/20 border border-primary/30 flex items-center justify-center">
                <Camera size={13} className="text-primary" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-foreground leading-tight flex items-center gap-1.5">
                  {selectedCamera.name}
                  <span className="text-[10px] font-medium text-emerald-400 flex items-center gap-0.5">
                    <span className="w-1 h-1 rounded-full bg-emerald-400 inline-block" />
                    {selectedCamera.status === "online" ? "Online" : "Offline"}
                  </span>
                </h2>
                <p className="text-[10px] text-muted-foreground">{selectedCamera.siteId.toUpperCase()} &bull; {selectedCamera.nvrName} &bull; Channel {selectedCamera.channel}</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><RefreshCw size={13} /></button>
              <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><Maximize2 size={13} /></button>
            </div>
          </div>
          <div className="flex gap-0 border-b border-border mt-2">
            {(["overview", "information", "stream", "events"] as ActiveTab[]).map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)} className={`px-3 py-2 text-[11px] font-medium capitalize border-b-2 -mb-px transition-colors ${activeTab === tab ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === "overview" && (
            <>
              <section>
                <div className="flex items-center gap-1.5 mb-2">
                  <Info size={11} className="text-muted-foreground" />
                  <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">Camera Information</h3>
                </div>
                <div className="bg-card rounded border border-border divide-y divide-border">
                  {infoRows.map(({ label, value }) => (
                    <div key={label} className="flex items-center justify-between px-3 py-2">
                      <span className="text-[11px] text-muted-foreground">{label}</span>
                      <span className="text-[11px] text-foreground font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              </section>
              <section>
                <div className="flex items-center gap-1.5 mb-2">
                  <Activity size={11} className="text-muted-foreground" />
                  <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">Stream Info</h3>
                </div>
                <div className="bg-card rounded border border-border divide-y divide-border">
                  {streamRows.map(({ label, value }) => (
                    <div key={label} className="flex items-center justify-between px-3 py-2">
                      <span className="text-[11px] text-muted-foreground">{label}</span>
                      <span className="text-[11px] text-foreground font-medium">{value}</span>
                    </div>
                  ))}
                </div>
              </section>
              <section>
                <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide mb-2">Actions</h3>
                <div className="flex items-center gap-2">
                  <button onClick={() => setStreamLoaded(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary/90 text-white text-[11px] font-medium rounded transition-colors">
                    <Video size={12} />Preview
                  </button>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 bg-transparent border border-border hover:bg-secondary text-foreground text-[11px] font-medium rounded transition-colors">
                    <Play size={12} />Playback
                  </button>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 bg-transparent border border-border hover:bg-secondary text-foreground text-[11px] font-medium rounded transition-colors">
                    <RefreshCw size={12} />Refresh
                  </button>
                </div>
              </section>
            </>
          )}
          {activeTab === "information" && (
            <div className="bg-card rounded border border-border divide-y divide-border">
              {infoRows.map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between px-3 py-2.5">
                  <span className="text-[11px] text-muted-foreground">{label}</span>
                  <span className="text-[11px] text-foreground font-medium">{value}</span>
                </div>
              ))}
            </div>
          )}
          {activeTab === "stream" && (
            <div className="bg-card rounded border border-border divide-y divide-border">
              {streamRows.map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between px-3 py-2.5">
                  <span className="text-[11px] text-muted-foreground">{label}</span>
                  <span className="text-[11px] text-foreground font-medium">{value}</span>
                </div>
              ))}
            </div>
          )}
          {activeTab === "events" && (
            <div className="space-y-2">
              {[
                { time: "10:35:40", msg: "Camera connected", type: "info" },
                { time: "09:12:05", msg: "Motion detected", type: "warn" },
                { time: "08:00:00", msg: "Stream started", type: "info" },
              ].map((evt, i) => (
                <div key={i} className="flex items-start gap-2.5 p-2.5 bg-card rounded border border-border">
                  <Clock size={11} className="text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-[11px] text-foreground">{evt.msg}</p>
                    <p className="text-[10px] text-muted-foreground">{evt.time}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Preview Panel */}
      <section className="flex-1 flex flex-col bg-background min-w-0">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border flex-shrink-0">
          <span className="text-xs font-semibold text-foreground">Preview</span>
          <div className="flex items-center gap-1">
            <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><RefreshCw size={13} /></button>
            <button onClick={() => setStreamLoaded(false)} className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><Minimize2 size={13} /></button>
            <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><Maximize2 size={13} /></button>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center bg-[#0a0f18] relative">
          {streamLoaded ? (
            <div className="w-full h-full flex items-center justify-center relative">
              <div className="absolute inset-0 opacity-5" style={{ backgroundImage: "linear-gradient(rgba(59,130,246,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(59,130,246,0.3) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
              <div className="flex flex-col items-center gap-3 text-center">
                <div className="relative">
                  <div className="w-16 h-16 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                    <Video size={28} className="text-primary" />
                  </div>
                  <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">Live Stream</p>
                  <p className="text-xs text-muted-foreground">{selectedCamera.name} &bull; {selectedCamera.nvrName}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">2560×1520 &bull; RTSP &bull; 20fps</p>
                </div>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-[10px] font-medium text-red-400 uppercase tracking-wide">Recording</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 text-center px-8">
              <div className="w-14 h-14 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
                <Camera size={24} className="text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">No stream loaded</p>
                <p className="text-xs text-muted-foreground mt-1">Click Preview to start the live stream</p>
              </div>
              <button onClick={() => setStreamLoaded(true)} className="mt-1 flex items-center gap-1.5 px-4 py-1.5 bg-primary hover:bg-primary/90 text-white text-xs font-medium rounded transition-colors">
                <Video size={12} />Start Preview
              </button>
            </div>
          )}
        </div>
        <div className="flex items-center justify-between px-4 py-2 border-t border-border flex-shrink-0">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Ratio size={12} /><span>16:9</span>
          </div>
          <div className="flex items-center gap-1">
            <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><ZoomOut size={13} /></button>
            <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><ZoomIn size={13} /></button>
            <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><Maximize2 size={13} /></button>
            <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground"><CircleDot size={13} /></button>
          </div>
        </div>
      </section>
    </>
  );
}

// ─── Dashboard Sidebar ────────────────────────────────────────────────────────

function DashboardSidebar({ activeNav, setActiveNav }: { activeNav: ActiveNav; setActiveNav: (v: ActiveNav) => void }) {
  const mainNav = navItems.filter((n) => n.section === "main");
  const mgmtNav = navItems.filter((n) => n.section === "management");
  const bottomNav = navItems.filter((n) => n.section === "bottom");

  return (
    <aside className="w-48 flex flex-col border-r border-border bg-[#0f1623] flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <div className="w-6 h-6 bg-primary rounded flex items-center justify-center flex-shrink-0">
          <Camera size={13} className="text-white" />
        </div>
        <span className="text-xs font-semibold tracking-wide text-foreground">SAMATOR</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-widest px-2 mb-1">Dashboard</p>
        {mainNav.map(({ icon: Icon, label }) => (
          <button key={label} onClick={() => setActiveNav(label)} className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded text-[11px] font-medium mb-0.5 transition-colors ${activeNav === label ? "bg-accent/50 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"}`}>
            <Icon size={14} className="flex-shrink-0" />
            {label}
          </button>
        ))}

        <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-widest px-2 mb-1 mt-4">Management</p>
        {mgmtNav.map(({ icon: Icon, label }) => (
          <button key={label} onClick={() => setActiveNav(label)} className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded text-[11px] font-medium mb-0.5 transition-colors ${activeNav === label ? "bg-accent/50 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"}`}>
            <Icon size={14} className="flex-shrink-0" />
            {label}
          </button>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-2 py-3 border-t border-border space-y-0.5">
        {bottomNav.map(({ icon: Icon, label }) => (
          <button key={label} onClick={() => setActiveNav(label)} className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded text-[11px] font-medium transition-colors ${activeNav === label ? "bg-accent/50 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"}`}>
            <Icon size={14} className="flex-shrink-0" />
            {label}
          </button>
        ))}
        <button className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors">
          <ChevronLeft size={14} className="flex-shrink-0" />
          Collapse
        </button>
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-border flex items-center gap-2">
        <div className="w-5 h-5 rounded bg-primary/30 border border-primary/40 flex items-center justify-center text-[9px] font-semibold text-primary flex-shrink-0">A</div>
        <div className="min-w-0">
          <p className="text-[10px] font-medium text-foreground truncate">Admin</p>
          <p className="text-[9px] text-muted-foreground truncate">admin@samator.id</p>
        </div>
      </div>
    </aside>
  );
}

// ─── Sites Sidebar (icon only) ─────────────────────────────────────────────────

function SitesSidebar({ activeNav, setActiveNav }: { activeNav: ActiveNav; setActiveNav: (v: ActiveNav) => void }) {
  return (
    <aside className="w-12 flex flex-col border-r border-border bg-[#0f1623] flex-shrink-0">
      <nav className="flex-1 flex flex-col py-2 gap-0.5">
        {siteNavItems.map(({ icon: Icon, label }) => (
          <button key={label} onClick={() => setActiveNav(label)} title={label} className={`w-full flex items-center justify-center py-2.5 relative group transition-colors ${activeNav === label ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}>
            {activeNav === label && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r" />}
            <Icon size={17} />
            <span className="absolute left-full ml-2 bg-popover border border-border text-foreground text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-50 transition-opacity shadow-lg">{label}</span>
          </button>
        ))}
      </nav>
      <div className="border-t border-border py-3 flex flex-col gap-1.5 px-1">
        {[{ label: "Sites", value: "12" }, { label: "Devices", value: "34" }, { label: "Cameras", value: "342" }, { label: "Streams", value: "245" }].map(({ label, value }) => (
          <div key={label} className="flex flex-col items-center">
            <span className="text-[11px] font-semibold text-foreground leading-tight">{value}</span>
            <span className="text-[8px] text-muted-foreground leading-tight">{label}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [activeNav, setActiveNav] = useState<ActiveNav>("Dashboard");
  const isDashboard = activeNav === "Dashboard";

  return (
    <div className="dark w-screen h-screen flex flex-col overflow-hidden bg-background text-foreground font-['Inter',sans-serif]">
      {/* Top Nav */}
      <header className="flex items-center h-11 px-4 border-b border-border bg-[#0f1623] flex-shrink-0 gap-3">
        {!isDashboard && (
          <>
            <div className="flex items-center gap-2 min-w-[160px]">
              <div className="w-6 h-6 bg-primary rounded flex items-center justify-center flex-shrink-0">
                <Camera size={13} className="text-white" />
              </div>
              <span className="text-sm font-semibold tracking-wide text-foreground">SAMATOR</span>
            </div>
            <div className="w-px h-5 bg-border" />
          </>
        )}
        {isDashboard && <div className="min-w-[192px]" />}

        <nav className="flex items-center gap-1 text-xs text-muted-foreground flex-1 min-w-0">
          {isDashboard ? (
            <span className="text-foreground font-medium">Dashboard</span>
          ) : (
            <>
              <span className="hover:text-foreground cursor-pointer">Sites</span>
              <ChevronRight size={12} />
              <span className="hover:text-foreground cursor-pointer">KZL-01</span>
              <ChevronRight size={12} />
              <span className="text-foreground font-medium">DS-7832NXI-K2</span>
            </>
          )}
        </nav>

        <div className="flex items-center gap-1.5 text-xs">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
          <span className="text-emerald-400 whitespace-nowrap">All System Operational</span>
        </div>

        <div className="flex items-center gap-2 bg-[#1e2a3b] border border-border rounded px-2.5 py-1 w-44">
          <Search size={12} className="text-muted-foreground flex-shrink-0" />
          <input type="text" placeholder="Search..." className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full" />
        </div>

        <button className="relative p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
          <Bell size={15} />
          <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-primary rounded-full" />
        </button>

        <div className="flex items-center gap-2 pl-1">
          <div className="w-6 h-6 rounded bg-primary/30 border border-primary/40 flex items-center justify-center text-[10px] font-semibold text-primary">A</div>
          <span className="text-xs text-foreground">Admin</span>
          <ChevronDown size={12} className="text-muted-foreground" />
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {isDashboard ? (
          <>
            <DashboardSidebar activeNav={activeNav} setActiveNav={setActiveNav} />
            <DashboardView />
          </>
        ) : (
          <>
            <SitesSidebar activeNav={activeNav} setActiveNav={setActiveNav} />
            <SitesView />
          </>
        )}
      </div>
    </div>
  );
}
