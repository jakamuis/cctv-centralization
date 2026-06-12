import { useState, useEffect, useCallback, useRef } from "react";
import DashboardView from "./DashboardView";
import {
  LayoutDashboard,
  Monitor,
  Play,
  Bell,
  Settings,
  Camera,
  Server,
  Search,
  RefreshCw,
  Maximize2,
  Minimize2,
  Video,
  ZoomIn,
  ZoomOut,
  Ratio,
  CircleDot,
  Info,
  Activity,
  Filter,
  SortAsc,
  ChevronRight,
  ChevronLeft,
  LogOut,
  LayoutGrid,
  Square,
  Sun,
  Moon,
  Eye,
  CalendarDays,
  Users,
  Map,
  ShieldCheck,
  FileText,
} from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { discoveryApi } from "../api";
import PlaybackView from "./Playback";
import DevicesPage from "./Devices";
import AlertsPage from "./Alerts";
import UsersPage from "./Users";
import RolesPermissionsPage from "./RolesPermissions";

// ─── Constants ────────────────────────────────────────────────────────────────

/**
 * Full nav item list.
 *
 * `roles` lists which NORMALISED role keys can see each item.
 * Normalised keys (produced by resolveRole below):
 *   "admin"    → SUPER_ADMIN  — full access
 *   "operator" → OPERATOR     — monitoring, playback, alerts
 *   "viewer"   → VIEWER       — monitoring only
 */
const ALL_NAV_ITEMS = [
  { icon: LayoutDashboard, label: "Dashboard",          section: "main",       roles: ["admin", "operator", "viewer"] },
  { icon: Eye,             label: "Live Streams",        section: "main",       roles: ["admin", "operator", "viewer"] },
  { icon: Monitor,         label: "Monitoring",          section: "main",       roles: ["admin", "operator", "viewer"] },
  { icon: Play,            label: "Playback",            section: "main",       roles: ["admin", "operator"] },
  { icon: Bell,            label: "Alerts",              section: "main",       roles: ["admin", "operator"] },
  { icon: Server,          label: "Devices",             section: "management", roles: ["admin"] },
  { icon: Camera,          label: "Camera Groups",       section: "management", roles: ["admin"] },
  { icon: Map,             label: "Maps",                section: "management", roles: ["admin"] },
  { icon: Users,           label: "Users",               section: "management", roles: ["admin"] },
  { icon: ShieldCheck,     label: "Roles & Permissions", section: "management", roles: ["admin"] },
  { icon: FileText,        label: "Audit Logs",          section: "management", roles: ["admin"] },
  { icon: Settings,        label: "Settings",            section: "bottom",     roles: ["admin"] },
];

/**
 * Resolve any role value (mapped or raw backend) to a normalised key.
 *
 * Handles both:
 *   - Already-mapped values from AuthContext: "admin", "operator", "viewer"
 *   - Raw backend values (in case of stale session): "SUPER_ADMIN", "OPERATOR", "VIEWER"
 */
function resolveRole(role) {
  if (!role) return "viewer";
  const r = String(role).toUpperCase().trim();
  if (r === "SUPER_ADMIN" || r === "ADMIN") return "admin";
  if (r === "OPERATOR")                     return "operator";
  if (r === "VIEWER")                       return "viewer";
  // Already lowercase-mapped
  const lower = String(role).toLowerCase().trim();
  if (lower === "admin")    return "admin";
  if (lower === "operator") return "operator";
  return "viewer";
}

/** Filter nav items by role — accepts both mapped and raw backend role values */
function getNavItems(role) {
  const r = resolveRole(role);
  return ALL_NAV_ITEMS.filter((item) => item.roles.includes(r));
}

/** Role badge label */
function roleBadge(role) {
  const r = resolveRole(role);
  if (r === "admin")    return "Admin";
  if (r === "operator") return "Operator";
  return "Viewer";
}

/** First letter of username for avatar */
function avatarLetter(username) {
  return (username || "U").charAt(0).toUpperCase();
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function StatusDot({ status }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
        status === "online" ? "bg-emerald-400" : "bg-red-500"
      }`}
    />
  );
}

function StatusBadge({ status }) {
  return (
    <span
      className={`text-[11px] font-medium px-2 py-0.5 rounded ${
        status === "online"
          ? "bg-emerald-500/15 text-emerald-400"
          : "bg-red-500/15 text-red-400"
      }`}
    >
      {status === "online" ? "Online" : "Offline"}
    </span>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function AppSidebar({ activeNav, onNavigate, user, onLogout }) {
  const navItems  = getNavItems(user?.role);
  const mainNav   = navItems.filter((n) => n.section === "main");
  const mgmtNav   = navItems.filter((n) => n.section === "management");
  const btmNav    = navItems.filter((n) => n.section === "bottom");

  function NavBtn({ icon: Icon, label }) {
    const isActive = activeNav === label;
    return (
      <button
        onClick={() => onNavigate(label)}
        className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded text-[15px] font-medium mb-0.5 transition-colors ${
          isActive
            ? "bg-accent/50 text-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
        }`}
      >
        <Icon size={18} className="flex-shrink-0" />
        {label}
      </button>
    );
  }

  return (
    <aside className="w-52 flex flex-col border-r border-border bg-sidebar flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
        <div className="w-8 h-8 bg-primary rounded flex items-center justify-center flex-shrink-0">
          <Camera size={17} className="text-white" />
        </div>
        <span className="text-sm font-semibold tracking-wide text-foreground">SAMATOR</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {mainNav.length > 0 && (
          <>
            <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest px-2 mb-2">
              Dashboard
            </p>
            {mainNav.map(({ icon, label }) => (
              <NavBtn key={label} icon={icon} label={label} />
            ))}
          </>
        )}

        {mgmtNav.length > 0 && (
          <>
            <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest px-2 mb-2 mt-6">
              Management
            </p>
            {mgmtNav.map(({ icon, label }) => (
              <NavBtn key={label} icon={icon} label={label} />
            ))}
          </>
        )}
      </nav>

      {/* Bottom nav items (e.g. Settings — admin only) */}
      {btmNav.length > 0 && (
        <div className="px-3 py-3 border-t border-border space-y-0.5">
          {btmNav.map(({ icon, label }) => (
            <NavBtn key={label} icon={icon} label={label} />
          ))}
        </div>
      )}

      {/* Footer: user info + logout */}
      <div className="px-4 py-3 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-primary/30 border border-primary/40 flex items-center justify-center text-xs font-semibold text-primary flex-shrink-0">
            {avatarLetter(user?.username)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">
              {user?.username || "User"}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {roleBadge(user?.role)}
            </p>
          </div>
          <button
            onClick={onLogout}
            title="Sign out"
            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-red-400 transition-colors flex-shrink-0"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}

// ─── Branches Pane ────────────────────────────────────────────────────────────

function BranchesPane({ branches, loading, error, selectedBranchId, onSelectBranch }) {
  const [search, setSearch] = useState("");

  const filtered = branches.filter((b) =>
    search === "" ||
    (b.name || b.code || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <aside className="w-56 flex flex-col border-r border-border bg-card flex-shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-3.5 py-3 border-b border-border">
        <span className="text-sm font-semibold text-foreground">Branches</span>
        <div className="flex items-center gap-1">
          <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
            <Filter size={13} />
          </button>
          <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
            <SortAsc size={13} />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-3.5 py-2.5 border-b border-border">
        <div className="flex items-center gap-2 bg-muted border border-border rounded px-2.5 py-1.5">
          <Search size={12} className="text-muted-foreground flex-shrink-0" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search branches…"
            className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-1">
        {loading && (
          <div className="px-4 py-5 text-muted-foreground text-xs">Loading…</div>
        )}

        {!loading && error && (
          <div className="px-4 py-5 text-red-400 text-xs leading-relaxed">{error}</div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="px-4 py-5 text-muted-foreground text-xs">
            {search ? "No matches" : "No branches found"}
          </div>
        )}

        {!loading && !error &&
          filtered.map((branch) => {
            const isActive = selectedBranchId === branch.id;
            return (
              <button
                key={branch.id}
                onClick={() => onSelectBranch(branch)}
                className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 transition-colors relative ${
                  isActive
                    ? "bg-accent/40 text-primary"
                    : "text-foreground hover:bg-secondary/50"
                }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-primary rounded-r" />
                )}
                <Monitor
                  size={14}
                  className={`flex-shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`}
                />
                <div className="flex-1 min-w-0 text-left">
                  <span className="block truncate text-xs font-medium">
                    {branch.name || branch.code || `Branch ${branch.id}`}
                  </span>
                  {branch.ip && (
                    <span className="block truncate text-[10px] text-muted-foreground leading-tight">
                      {branch.ip}
                    </span>
                  )}
                </div>
                {branch.status && (
                  <StatusDot status={branch.status} />
                )}
              </button>
            );
          })}
      </div>

      {/* Footer count */}
      <div className="px-3.5 py-2 border-t border-border">
        <span className="text-[10px] text-muted-foreground">
          {branches.length} branch{branches.length !== 1 ? "es" : ""}
        </span>
      </div>
    </aside>
  );
}

// ─── Cameras Pane ─────────────────────────────────────────────────────────────

function CamerasPane({ cameras, loading, error, selectedCameraId, onSelectCamera, branchName }) {
  const [search, setSearch] = useState("");

  const filtered = cameras.filter((c) =>
    search === "" ||
    (c.name || c.stream_name || "").toLowerCase().includes(search.toLowerCase())
  );

  const onlineCount  = cameras.filter((c) => c.status === "online").length;
  const offlineCount = cameras.filter((c) => c.status !== "online").length;

  return (
    <aside className="w-64 flex flex-col border-r border-border bg-card flex-shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-3.5 py-3 border-b border-border">
        <div className="min-w-0">
          <span className="text-sm font-semibold text-foreground block truncate">
            {branchName || "Cameras"}
          </span>
          {branchName && (
            <span className="text-[10px] text-muted-foreground">
              <span className="text-emerald-400">{onlineCount}</span> online &bull;{" "}
              <span className="text-red-400">{offlineCount}</span> offline
            </span>
          )}
        </div>
        <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
          <Filter size={13} />
        </button>
      </div>

      {/* Search */}
      <div className="px-3.5 py-2.5 border-b border-border">
        <div className="flex items-center gap-2 bg-muted border border-border rounded px-2.5 py-1.5">
          <Search size={12} className="text-muted-foreground flex-shrink-0" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cameras…"
            className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-1">
        {loading && (
          <div className="px-4 py-5 text-muted-foreground text-xs">Loading…</div>
        )}

        {!loading && error && (
          <div className="px-4 py-5 text-red-400 text-xs leading-relaxed">{error}</div>
        )}

        {!loading && !error && !branchName && (
          <div className="px-4 py-5 text-muted-foreground text-xs text-center leading-relaxed">
            Select a branch<br />to view cameras
          </div>
        )}

        {!loading && !error && branchName && filtered.length === 0 && (
          <div className="px-4 py-5 text-muted-foreground text-xs">
            {search ? "No matches" : "No cameras in this branch"}
          </div>
        )}

        {!loading && !error &&
          filtered.map((cam) => {
            const isActive = selectedCameraId === cam.id;
            const isOnline = cam.status === "online";
            return (
              <button
                key={cam.id}
                onClick={() => onSelectCamera(cam)}
                className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 transition-colors relative ${
                  isActive
                    ? "bg-accent/40 text-primary"
                    : "text-foreground hover:bg-secondary/50"
                }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-primary rounded-r" />
                )}
                <Camera
                  size={14}
                  className={`flex-shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`}
                />
                <div className="flex-1 min-w-0 text-left">
                  <p className="truncate text-xs font-medium leading-tight">
                    {cam.name || cam.stream_name || `Camera ${cam.id}`}
                  </p>
                  {cam.channel_number != null && (
                    <p className="text-[10px] text-muted-foreground leading-tight">
                      Ch {cam.channel_number}
                    </p>
                  )}
                </div>
                <StatusDot status={isOnline ? "online" : "offline"} />
              </button>
            );
          })}
      </div>

      {/* Footer count */}
      {branchName && (
        <div className="px-3.5 py-2 border-t border-border">
          <span className="text-[10px] text-muted-foreground">
            {cameras.length} camera{cameras.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}
    </aside>
  );
}

// ─── Inline MSE Player ────────────────────────────────────────────────────────
// Mirrors DiscoveryLivePlayer but renders a bare <video> with no wrapper CSS.

function MsePlayer({ streamName, onError }) {
  const videoRef = useRef(null);
  const wsRef    = useRef(null);
  const msRef    = useRef(null);
  const sbRef    = useRef(null);
  const bufRef   = useRef(new Uint8Array(2 * 1024 * 1024));
  const bufLen   = useRef(0);

  useEffect(() => {
    if (!streamName || !videoRef.current) return;

    // Cleanup previous session
    if (wsRef.current)  { try { wsRef.current.close()       } catch {} wsRef.current = null; }
    if (msRef.current)  { try { msRef.current.endOfStream()  } catch {} msRef.current = null; }
    sbRef.current = null;
    bufLen.current = 0;
    if (videoRef.current) { videoRef.current.src = ""; videoRef.current.load(); }

    const video = videoRef.current;
    video.muted = true;

    const CODECS = [
      "avc1.640029", "avc1.64002A", "avc1.640033",
      "hvc1.1.6.L153.B0",
      "mp4a.40.2", "mp4a.40.5", "opus",
    ];
    const supported = CODECS.filter((c) => {
      const type = c.includes("vc1") ? `video/mp4; codecs="${c}"` : `audio/mp4; codecs="${c}"`;
      return video.canPlayType(type) !== "";
    }).join(",");

    const ms = new MediaSource();
    msRef.current = ms;
    video.src = URL.createObjectURL(ms);

    ms.addEventListener("sourceopen", () => {
      URL.revokeObjectURL(video.src);

      // Connect directly to go2rtc (it has origin: "*" so cross-origin is allowed).
      // Vite dev server does not proxy /go2rtc/, so we cannot use window.location.host.
      const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const go2rtcHost = window.location.hostname === "localhost" ? "localhost:1984" : `${window.location.hostname}:1984`;
      const wsUrl   = `${wsProto}//${go2rtcHost}/api/ws?src=${encodeURIComponent(streamName)}`;
      const ws      = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      // If no binary video data arrives within 8 s the camera is unreachable
      let gotData = false;
      const noDataTimer = setTimeout(() => {
        if (!gotData) onError?.();
      }, 8000);

      ws.onopen = () => ws.send(JSON.stringify({ type: "mse", value: supported }));

      ws.onmessage = (ev) => {
        if (typeof ev.data === "string") {
          const msg = JSON.parse(ev.data);
          if (msg.type === "mse") {
            try {
              const sb = ms.addSourceBuffer(msg.value);
              sb.mode = "segments";
              sbRef.current = sb;
              sb.addEventListener("updateend", () => {
                if (!sb.updating && bufLen.current > 0) {
                  try { sb.appendBuffer(bufRef.current.slice(0, bufLen.current)); bufLen.current = 0; } catch {}
                }
                if (!sb.updating && sb.buffered && sb.buffered.length) {
                  const end   = sb.buffered.end(sb.buffered.length - 1);
                  const start = end - 5;
                  const s0    = sb.buffered.start(0);
                  if (start > s0) { try { sb.remove(s0, start); } catch {} }
                  if (video.currentTime < start) video.currentTime = start;
                }
              });
            } catch {}
          }
        } else {
          gotData = true;
          clearTimeout(noDataTimer);
          const sb = sbRef.current;
          if (!sb) return;
          const data = new Uint8Array(ev.data);
          if (sb.updating || bufLen.current > 0) {
            bufRef.current.set(data, bufLen.current);
            bufLen.current += data.byteLength;
          } else {
            try { sb.appendBuffer(ev.data); } catch {}
          }
        }
      };

      ws.onerror = () => { clearTimeout(noDataTimer); if (!gotData) onError?.(); };
      ws.onclose = () => { clearTimeout(noDataTimer); wsRef.current = null; if (!gotData) onError?.(); };
    }, { once: true });

    video.addEventListener("canplay", () => {
      video.muted = true;
      video.play().catch(() => {});
    }, { once: true });

    return () => {
      if (wsRef.current)  { try { wsRef.current.close()       } catch {} wsRef.current = null; }
      if (msRef.current)  { try { msRef.current.endOfStream()  } catch {} msRef.current = null; }
      sbRef.current = null;
      bufLen.current = 0;
      if (videoRef.current) { videoRef.current.src = ""; videoRef.current.load(); }
    };
  }, [streamName]);

  return (
    <video
      ref={videoRef}
      muted
      playsInline
      autoPlay
      style={{ display: "block", width: "100%", height: "100%", objectFit: "contain", background: "#000" }}
    />
  );
}

// ─── Grid Cell ────────────────────────────────────────────────────────────────
// Self-contained cell that registers its own stream and plays it.

function GridCell({ camera, branch, onStatusChange }) {
  const [streamName, setStreamName] = useState(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!camera || !branch) return;
    setStreamName(null);
    setLoading(true);
    setFailed(false);
    discoveryApi
      .startChannelStream(branch.id, camera.channel_id)
      .then((res) => {
        if (res?.stream_name) {
          setStreamName(res.stream_name);
          onStatusChange?.(camera.id, "online");
        } else {
          setFailed(true);
          onStatusChange?.(camera.id, "offline");
        }
      })
      .catch(() => {
        setFailed(true);
        onStatusChange?.(camera.id, "offline");
      })
      .finally(() => setLoading(false));
  }, [camera?.id, branch?.id]);

  const camName = camera?.name || `Camera ${camera?.id}`;
  // Use actual stream state for the dot — overrides initial estimate
  const dotStatus = streamName ? "online" : failed ? "offline" : camera?.status;

  return (
    <div className="relative bg-black rounded overflow-hidden border border-border">
      {streamName ? (
        <MsePlayer
          key={streamName}
          streamName={streamName}
          onError={() => {
            setFailed(true);
            onStatusChange?.(camera.id, "offline");
          }}
        />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
          <Camera size={18} className="text-muted-foreground" />
          {loading ? (
            <p className="text-[10px] text-muted-foreground">Connecting…</p>
          ) : failed ? (
            <p className="text-[10px] text-red-400">Unavailable</p>
          ) : null}
        </div>
      )}
      {/* Name overlay */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent px-2 py-1.5 pointer-events-none">
        <div className="flex items-center gap-1.5">
          <StatusDot status={dotStatus} />
          <span className="text-[10px] text-white font-medium truncate">{camName}</span>
        </div>
      </div>
    </div>
  );
}

// ─── Live Preview Pane ────────────────────────────────────────────────────────
// Split into two sub-columns:
//   Left  (flex-1): compact video player
//   Right (w-72):   camera info panel

function LivePreviewPane({ camera, branch, streamName, streamLoading, cameras, onCameraStatusChange }) {
  const [streamLoaded, setStreamLoaded] = useState(false);
  const [viewMode,     setViewMode]     = useState("grid"); // "single" | "grid"
  const [gridCols,     setGridCols]     = useState(2);        // 2 → 2×2, 3 → 3×3
  const [gridPage,     setGridPage]     = useState(0);

  // Reset preview state whenever the selected camera changes
  useEffect(() => {
    setStreamLoaded(false);
  }, [camera?.id]);

  // Auto-start player once stream is registered
  useEffect(() => {
    if (streamName) setStreamLoaded(true);
  }, [streamName]);

  // Reset page when branch or grid size changes
  useEffect(() => {
    setGridPage(0);
  }, [branch?.id, gridCols]);

  const camName    = camera?.name || camera?.stream_name || "—";
  const branchName = branch?.name || branch?.code || "—";
  const isOnline   = camera?.status === "online";

  // Real channel metadata from the normalised camera object
  const channelProtocol = camera?._raw?.protocol || "RTSP";
  const channelIp       = camera?._raw?.ip_address || null;

  // NVR metadata from the normalised branch object
  const nvrIp     = branch?.ip || null;
  const nvrModel  = branch?._raw?.model || null;
  const nvrName   = branch?.name || branch?.code || null;
  const rawVendor = branch?._raw?.vendor || "hikvision";
  const nvrVendor = rawVendor === "acti_snvr" ? "ACTi SNVR" : "Hikvision";

  const streamMeta = {
    protocol:   channelProtocol,
    // Stream name is set once the backend registers it with go2rtc
    stream:     streamName || (streamLoading ? "Registering…" : "—"),
    channel:    camera?.channel_number != null ? `Ch ${camera.channel_number}` : "—",
    ip:         channelIp || nvrIp || "—",
  };

  return (
    <section className="flex-1 flex flex-col bg-background min-w-0 overflow-hidden">
      {/* Pane header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-sm font-semibold text-foreground">Live Preview</span>
          {viewMode === "single" && camera && (
            <>
              <span className="text-border text-muted-foreground">·</span>
              <span className="text-xs text-muted-foreground truncate">{camName}</span>
              <StatusBadge status={isOnline ? "online" : "offline"} />
            </>
          )}
          {viewMode === "grid" && branch && (
            <>
              <span className="text-border text-muted-foreground">·</span>
              <span className="text-xs text-muted-foreground truncate">
                {branch.name || branch.code} — {gridCols}×{gridCols}
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* View mode toggle */}
          <div className="flex items-center rounded border border-border overflow-hidden">
            <button
              onClick={() => setViewMode("single")}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                viewMode === "single"
                  ? "bg-primary text-white"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <Square size={12} />
              Single
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                viewMode === "grid"
                  ? "bg-primary text-white"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <LayoutGrid size={12} />
              Grid
            </button>
          </div>

          {/* Grid size selector — only visible in grid mode */}
          {viewMode === "grid" && (
            <div className="flex items-center rounded border border-border overflow-hidden">
              {[2, 3].map((n) => (
                <button
                  key={n}
                  onClick={() => setGridCols(n)}
                  className={`px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                    gridCols === n
                      ? "bg-primary text-white"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                  }`}
                >
                  {n}×{n}
                </button>
              ))}
            </div>
          )}

          <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
            <RefreshCw size={14} />
          </button>
          <button
            onClick={() => setStreamLoaded(false)}
            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
          >
            <Minimize2 size={14} />
          </button>
          <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      {/* Grid view body */}
      {viewMode === "grid" && (() => {
        const perPage   = gridCols * gridCols;
        const camList   = cameras || [];
        const pageCount = Math.max(1, Math.ceil(camList.length / perPage));
        const pageCams  = camList.slice(gridPage * perPage, (gridPage + 1) * perPage);
        return (
          <div className="flex-1 flex flex-col bg-[#0a0f18] min-h-0">
            {!branch ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center">
                <div className="w-14 h-14 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
                  <LayoutGrid size={22} className="text-muted-foreground" />
                </div>
                <p className="text-sm font-medium text-foreground">No branch selected</p>
                <p className="text-xs text-muted-foreground">Select a branch to view its cameras in the grid</p>
              </div>
            ) : camList.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center">
                <Camera size={22} className="text-muted-foreground" />
                <p className="text-xs text-muted-foreground">No cameras in this branch</p>
              </div>
            ) : (
              <>
                <div className="flex-1 p-3 min-h-0">
                  <div
                    className="grid gap-1.5 h-full"
                    style={{ gridTemplateColumns: `repeat(${gridCols}, 1fr)`, gridTemplateRows: `repeat(${gridCols}, 1fr)` }}
                  >
                    {Array.from({ length: perPage }).map((_, i) => {
                      const cam = pageCams[i];
                      return cam ? (
                        <GridCell key={cam.id} camera={cam} branch={branch} onStatusChange={onCameraStatusChange} />
                      ) : (
                        <div key={`empty-${i}`} className="bg-black/40 rounded border border-border flex items-center justify-center">
                          <Camera size={18} className="text-muted-foreground/30" />
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Page navigation */}
                {pageCount > 1 && (
                  <div className="flex items-center justify-center gap-3 py-2 border-t border-border bg-card flex-shrink-0">
                    <button
                      onClick={() => setGridPage((p) => Math.max(0, p - 1))}
                      disabled={gridPage === 0}
                      className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <div className="flex items-center gap-1.5">
                      {Array.from({ length: pageCount }).map((_, i) => (
                        <button
                          key={i}
                          onClick={() => setGridPage(i)}
                          className={`w-2 h-2 rounded-full transition-colors ${
                            i === gridPage ? "bg-primary" : "bg-border hover:bg-muted-foreground"
                          }`}
                        />
                      ))}
                    </div>
                    <button
                      onClick={() => setGridPage((p) => Math.min(pageCount - 1, p + 1))}
                      disabled={gridPage === pageCount - 1}
                      className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        );
      })()}

      {/* Single view body: video left + info right */}
      {viewMode === "single" && <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ── Left: Video player ── */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#0a0f18]">
          {/* Video container — 16:9, centered, compact */}
          <div className="flex-1 flex items-center justify-center p-5 min-h-0">
            <div
              className="relative bg-black rounded-lg border border-border overflow-hidden w-full"
              style={{ maxWidth: "520px", aspectRatio: "16/9" }}
            >
              {!camera ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                  <div className="w-14 h-14 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
                    <Camera size={24} className="text-muted-foreground" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-foreground">No camera selected</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Select a branch and camera to preview
                    </p>
                  </div>
                </div>
              ) : streamLoaded ? (
                streamName ? (
                  <div className="absolute inset-0">
                    <MsePlayer key={streamName} streamName={streamName} />
                  </div>
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                    <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                      <Video size={26} className="text-primary animate-pulse" />
                    </div>
                    <p className="text-xs text-muted-foreground">Registering stream…</p>
                  </div>
                )
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                  <div className="w-14 h-14 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
                    <Camera size={24} className="text-muted-foreground" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-foreground">{camName}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {streamLoading
                        ? "Registering stream…"
                        : "Click Preview to start live stream"}
                    </p>
                  </div>
                  <button
                    onClick={() => setStreamLoaded(true)}
                    disabled={streamLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded transition-colors"
                  >
                    <Video size={13} />
                    {streamLoading ? "Registering…" : "Start Preview"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Video controls bar */}
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-border flex-shrink-0 bg-card">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Ratio size={13} />
              <span>16:9</span>
            </div>
            <div className="flex items-center gap-1">
              <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
                <ZoomOut size={14} />
              </button>
              <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
                <ZoomIn size={14} />
              </button>
              <button className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
                <Maximize2 size={14} />
              </button>
              {camera && (
                <button
                  onClick={() => setStreamLoaded((v) => !v)}
                  className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                >
                  <CircleDot size={14} className={streamLoaded ? "text-red-400" : ""} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ── Right: Camera Info Panel ── */}
        <div className="w-72 flex flex-col border-l border-border bg-card flex-shrink-0 overflow-y-auto">
          {/* Panel header */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border flex-shrink-0">
            <Info size={14} className="text-muted-foreground" />
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Camera Info
            </span>
          </div>

          {!camera ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 px-4 py-8 text-center">
              <div className="w-12 h-12 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
                <Camera size={20} className="text-muted-foreground" />
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Select a camera to view its details
              </p>
            </div>
          ) : (
            <>
              {/* Camera identity */}
              <div className="px-4 py-3 border-b border-border">
                <div className="flex items-center gap-2.5 mb-1">
                  <div className="w-8 h-8 rounded bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                    <Camera size={15} className="text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground truncate">{camName}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{branchName}</p>
                  </div>
                </div>
                <div className="mt-2">
                  <StatusBadge status={isOnline ? "online" : "offline"} />
                </div>
              </div>

              {/* Info rows */}
              <div className="flex-1">
                {/* Camera details section */}
                <div className="px-4 pt-3 pb-1">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Info size={11} className="text-muted-foreground" />
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                      Details
                    </span>
                  </div>
                  <div className="bg-background rounded border border-border divide-y divide-border">
                    {[
                      { label: "Camera",  value: camName },
                      { label: "Branch",  value: branchName },
                      ...(nvrName ? [{ label: "NVR",    value: nvrName }] : []),
                      { label: "Vendor",  value: nvrVendor },
                      ...(nvrModel ? [{ label: "Model",  value: nvrModel }] : []),
                      { label: "Status",  value: isOnline ? "Online" : "Offline",
                        color: isOnline ? "text-emerald-400" : "text-red-400" },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="flex items-center justify-between px-3 py-2">
                        <span className="text-xs text-muted-foreground">{label}</span>
                        <span className={`text-xs font-medium truncate max-w-[140px] text-right ${color || "text-foreground"}`}>
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Stream info section */}
                <div className="px-4 pt-3 pb-1">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Activity size={11} className="text-muted-foreground" />
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                      Stream
                    </span>
                  </div>
                  <div className="bg-background rounded border border-border divide-y divide-border">
                    {[
                      { label: "Protocol", value: streamMeta.protocol },
                      { label: "Channel",  value: streamMeta.channel },
                      { label: "IP",       value: streamMeta.ip },
                      { label: "Stream",   value: streamMeta.stream },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex items-center justify-between px-3 py-2">
                        <span className="text-xs text-muted-foreground">{label}</span>
                        <span className="text-xs font-medium text-foreground font-mono truncate max-w-[140px] text-right">
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="px-4 py-3 border-t border-border flex flex-col gap-2 flex-shrink-0">
                <button
                  onClick={() => setStreamLoaded(true)}
                  disabled={streamLoading}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded transition-colors"
                >
                  <Video size={13} />
                  {streamLoading ? "Registering…" : "Preview Live Stream"}
                </button>
                <div className="flex gap-2">
                  <button className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-transparent border border-border hover:bg-secondary text-foreground text-xs font-medium rounded transition-colors">
                    <Play size={12} />
                    Playback
                  </button>
                  <button className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-transparent border border-border hover:bg-secondary text-foreground text-xs font-medium rounded transition-colors">
                    <RefreshCw size={12} />
                    Refresh
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>}
    </section>
  );
}

// ─── Placeholder views ────────────────────────────────────────────────────────

function PlaceholderView({ label }) {
  const icons = {
    Dashboard:            LayoutDashboard,
    "Live Streams":       Eye,
    Playback:             Play,
    Events:               CalendarDays,
    Alerts:               Bell,
    Devices:              Server,
    "Camera Groups":      Camera,
    Maps:                 Map,
    Users:                Users,
    "Roles & Permissions":ShieldCheck,
    "Audit Logs":         FileText,
    Settings:             Settings,
  };
  const Icon = icons[label] || Monitor;

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 bg-background">
      <div className="w-16 h-16 rounded-full bg-secondary/50 border border-border flex items-center justify-center">
        <Icon size={28} className="text-muted-foreground" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground mt-1">This section is coming soon</p>
      </div>
    </div>
  );
}

// ─── Data normalisation helpers ───────────────────────────────────────────────

/**
 * Map a raw NVR object from GET /discovery/nvrs into the shape the
 * BranchesPane expects:
 *   { id, name, code, ip, status }
 */
function normaliseNvr(nvr) {
  return {
    // keep the original for reference (needed when loading channels)
    _raw: nvr,
    id:     nvr.id,
    name:   nvr.branch_name || nvr.device_name || nvr.code || nvr.id,
    code:   nvr.code,
    ip:     nvr.nvr_ip,
    // treat "synced" as online; anything else (unreachable / auth_error / failed) as offline
    status: nvr.sync_status === "synced" ? "online" : "offline",
  };
}

/**
 * Map a raw channel object from GET /discovery/nvrs/{id}/channels into the
 * shape the CamerasPane expects:
 *   { id, name, channel_number, status }
 *
 * nvrOnline — pass the parent NVR's online status so a channel can only be
 * green when both the NVR is reachable AND the channel is enabled.
 */
function normaliseChannel(ch, nvrOnline = true) {
  return {
    _raw:           ch,
    id:             ch.id,
    name:           ch.channel_name || `Channel ${ch.channel_id}`,
    channel_number: ch.channel_id,
    status:         (nvrOnline && ch.is_enabled) ? "online" : "offline",
    channel_id:     ch.channel_id,
    lastOnline:     ch.last_online_at || null,
  };
}

// ─── Monitoring View ──────────────────────────────────────────────────────────

function MonitoringView() {
  const [branches,        setBranches]        = useState([]);
  const [cameras,         setCameras]         = useState([]);
  const [selectedBranch,  setSelectedBranch]  = useState(null);
  const [selectedCamera,  setSelectedCamera]  = useState(null);
  const [branchesLoading, setBranchesLoading] = useState(true);
  const [camerasLoading,  setCamerasLoading]  = useState(false);
  const [branchesError,   setBranchesError]   = useState(null);
  const [camerasError,    setCamerasError]    = useState(null);
  // stream_name returned by the backend after registering with go2rtc
  const [streamName,      setStreamName]      = useState(null);
  const [streamLoading,   setStreamLoading]   = useState(false);

  // ── Load NVRs as branches on mount ──────────────────────────────────────────
  useEffect(() => {
    setBranchesLoading(true);
    setBranchesError(null);
    discoveryApi
      .getNvrs()
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setBranches(list.map(normaliseNvr));
      })
      .catch((err) => {
        console.error("Failed to load NVRs:", err);
        setBranchesError("Failed to load branches. Please try again.");
        setBranches([]);
      })
      .finally(() => setBranchesLoading(false));
  }, []);

  // ── Select a branch → load its channels ─────────────────────────────────────
  const handleSelectBranch = useCallback((branch) => {
    setSelectedBranch(branch);
    setSelectedCamera(null);
    setStreamName(null);
    setCameras([]);
    setCamerasError(null);
    setCamerasLoading(true);
    discoveryApi
      .getChannels(branch.id)
      .then((data) => {
        // Response shape: { nvr_id, channels: [...] }
        const raw = Array.isArray(data) ? data : (data?.channels ?? []);
        const nvrOnline = branch.status === "online";
        setCameras(raw.map((ch) => normaliseChannel(ch, nvrOnline)));
      })
      .catch((err) => {
        console.error("Failed to load channels:", err);
        setCamerasError("Failed to load cameras. Please try again.");
        setCameras([]);
      })
      .finally(() => setCamerasLoading(false));
  }, []);

  // ── Update a single camera's status (called by GridCell on stream result) ────
  const handleCameraStatusChange = useCallback((cameraId, status) => {
    setCameras((prev) =>
      prev.map((c) => c.id === cameraId ? { ...c, status } : c)
    );
  }, []);

  // ── Select a camera → register stream with go2rtc ───────────────────────────
  const handleSelectCamera = useCallback((cam) => {
    setSelectedCamera(cam);
    setStreamName(null);

    if (!selectedBranch) return;

    setStreamLoading(true);
    discoveryApi
      .startChannelStream(selectedBranch.id, cam.channel_id)
      .then((res) => {
        if (res?.stream_name) {
          setStreamName(res.stream_name);
          setCameras((prev) =>
            prev.map((c) => c.id === cam.id ? { ...c, status: "online" } : c)
          );
        } else {
          setCameras((prev) =>
            prev.map((c) => c.id === cam.id ? { ...c, status: "offline" } : c)
          );
        }
      })
      .catch(() => {
        setCameras((prev) =>
          prev.map((c) => c.id === cam.id ? { ...c, status: "offline" } : c)
        );
      })
      .finally(() => setStreamLoading(false));
  }, [selectedBranch]);

  return (
    <>
      <BranchesPane
        branches={branches}
        loading={branchesLoading}
        error={branchesError}
        selectedBranchId={selectedBranch?.id}
        onSelectBranch={handleSelectBranch}
      />
      <CamerasPane
        cameras={cameras}
        loading={camerasLoading}
        error={camerasError}
        selectedCameraId={selectedCamera?.id}
        onSelectCamera={handleSelectCamera}
        branchName={selectedBranch?.name || selectedBranch?.code || null}
      />
      <LivePreviewPane
        camera={selectedCamera}
        branch={selectedBranch}
        streamName={streamName}
        streamLoading={streamLoading}
        cameras={cameras}
        onCameraStatusChange={handleCameraStatusChange}
      />
    </>
  );
}

// ─── Top Header ───────────────────────────────────────────────────────────────

function TopHeader({ activeNav, user }) {
  const { theme, toggleTheme } = useTheme();
  return (
    <header className="flex items-center h-12 px-4 border-b border-border bg-sidebar flex-shrink-0 gap-3">
      <nav className="flex items-center gap-1.5 text-xs text-muted-foreground flex-1 min-w-0">
        <span className="hover:text-foreground cursor-pointer">Home</span>
        <ChevronRight size={13} />
        <span className="text-foreground font-medium">{activeNav}</span>
      </nav>

      <div className="flex items-center gap-2 text-xs">
        <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
        <span className="text-emerald-400 whitespace-nowrap">All Systems Operational</span>
      </div>

      <div className="flex items-center gap-2 bg-secondary border border-border rounded px-3 py-1.5 w-44">
        <Search size={13} className="text-muted-foreground flex-shrink-0" />
        <input
          type="text"
          placeholder="Search…"
          className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
        />
      </div>

      <button
        onClick={toggleTheme}
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
      >
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>

      <button className="relative p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
        <Bell size={16} />
        <span className="absolute top-0.5 right-0.5 w-2 h-2 bg-primary rounded-full" />
      </button>

      <div className="flex items-center gap-2 pl-1">
        <div className="w-7 h-7 rounded bg-primary/30 border border-primary/40 flex items-center justify-center text-[11px] font-semibold text-primary">
          {avatarLetter(user?.username)}
        </div>
        <span className="text-xs text-foreground">{user?.username || "User"}</span>
      </div>
    </header>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────

export default function MonitoringApp({ user, onLogout }) {
  const [activeNav, setActiveNav] = useState("Dashboard");

  return (
    <div className="w-screen h-screen flex flex-col overflow-hidden bg-background text-foreground font-['Inter',sans-serif]">
      <TopHeader activeNav={activeNav} user={user} />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <AppSidebar
          activeNav={activeNav}
          onNavigate={setActiveNav}
          user={user}
          onLogout={onLogout}
        />

        <div className="flex flex-1 min-h-0 min-w-0 overflow-hidden">
          {activeNav === "Dashboard" ? (
            <DashboardView />
          ) : activeNav === "Monitoring" || activeNav === "Live Streams" ? (
            <MonitoringView />
          ) : activeNav === "Playback" ? (
            <PlaybackView />
          ) : activeNav === "Alerts" ? (
            <AlertsPage />
          ) : activeNav === "Devices" ? (
            <DevicesPage />
          ) : activeNav === "Users" ? (
            <UsersPage />
          ) : activeNav === "Roles & Permissions" ? (
            <RolesPermissionsPage />
          ) : (
            <PlaceholderView label={activeNav} />
          )}
        </div>
      </div>
    </div>
  );
}
