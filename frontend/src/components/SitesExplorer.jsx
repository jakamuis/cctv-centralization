import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, MapPin, Video } from "lucide-react";
import { useSitesStore } from "../store/sitesStore";
import { discoveryApi } from "../api";

// ─── Mock data (used when backend returns nothing) ───────────────────────────
const MOCK_BRANCHES = [
  {
    id: "branch-kendal",
    name: "Kendal",
    cameras: [
      { id: "cam-k1", name: "Main Gate", online: true },
      { id: "cam-k2", name: "Office LT1", online: true },
      { id: "cam-k3", name: "Warehouse", online: false },
    ],
  },
  {
    id: "branch-surabaya",
    name: "Surabaya",
    cameras: [
      { id: "cam-s1", name: "Loading Dock", online: true },
      { id: "cam-s2", name: "Parking Area", online: true },
    ],
  },
  {
    id: "branch-jakarta",
    name: "Jakarta",
    cameras: [
      { id: "cam-j1", name: "Lobby", online: true },
      { id: "cam-j2", name: "Server Room", online: false },
    ],
  },
];

// ─── Build branch tree from NVR discovery data ───────────────────────────────
function buildBranchesFromNvrs(nvrGroups) {
  const branchMap = new Map();

  nvrGroups.forEach(({ nvr, channels }) => {
    const branchKey = nvr.branch_name || nvr.code || nvr.nvr_ip || "Unknown";
    if (!branchMap.has(branchKey)) {
      branchMap.set(branchKey, {
        id: `branch-${branchKey}`,
        name: branchKey,
        cameras: [],
      });
    }
    channels.forEach((ch) => {
      branchMap.get(branchKey).cameras.push({
        id: `channel-${nvr.id}-${ch.channel_id}`,
        name: ch.channel_name || `Channel ${ch.channel_id}`,
        online: ch.is_enabled !== false,
        channel: ch,
        nvr,
      });
    });
  });

  return Array.from(branchMap.values());
}

// ─── Camera row ───────────────────────────────────────────────────────────────
function CameraRow({ camera, isSelected, onSelect }) {
  return (
    <button
      onClick={() => onSelect(camera)}
      className={`
        group flex items-center w-full text-left
        pl-8 pr-3 py-1.5 rounded
        transition-colors duration-100
        ${
          isSelected
            ? "bg-blue-600/25 text-blue-300"
            : "text-gray-400 hover:bg-gray-800/60 hover:text-gray-200"
        }
      `}
    >
      {/* Status dot */}
      <span
        className={`
          w-1.5 h-1.5 rounded-full flex-shrink-0 mr-2
          ${camera.online ? "bg-emerald-400" : "bg-red-500/70"}
        `}
      />
      <Video
        className={`w-3 h-3 flex-shrink-0 mr-1.5 ${
          isSelected ? "text-blue-400" : "text-gray-600 group-hover:text-gray-400"
        }`}
      />
      <span className="truncate text-xs">{camera.name}</span>
    </button>
  );
}

// ─── Branch row (expandable) ──────────────────────────────────────────────────
function BranchRow({ branch, selectedId, onSelect, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const onlineCount = branch.cameras.filter((c) => c.online).length;
  const total = branch.cameras.length;

  return (
    <div>
      {/* Branch header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="
          flex items-center w-full text-left
          px-3 py-2 rounded
          text-gray-300 hover:bg-gray-800/50 hover:text-white
          transition-colors duration-100
          group
        "
      >
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 flex-shrink-0 text-gray-500 mr-1.5" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 flex-shrink-0 text-gray-500 mr-1.5" />
        )}
        <MapPin className="w-3.5 h-3.5 flex-shrink-0 text-blue-500/70 mr-2" />
        <span className="flex-1 truncate text-xs font-semibold tracking-wide uppercase text-gray-300">
          {branch.name}
        </span>
        {/* Camera count badge */}
        <span className="ml-2 text-[10px] text-gray-600 tabular-nums flex-shrink-0">
          {onlineCount}/{total}
        </span>
      </button>

      {/* Camera list */}
      {open && (
        <div className="mb-1">
          {branch.cameras.length === 0 ? (
            <p className="pl-8 py-1 text-[11px] text-gray-600 italic">No cameras</p>
          ) : (
            branch.cameras.map((cam) => (
              <CameraRow
                key={cam.id}
                camera={cam}
                isSelected={selectedId === cam.id}
                onSelect={onSelect}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function SitesExplorer() {
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [usingMock, setUsingMock] = useState(false);
  const [filter, setFilter] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  const setSelectedCamera = useSitesStore((state) => state.setSelectedCamera);

  // Load data
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const nvrs = await discoveryApi.getNvrs();
        if (cancelled) return;

        if (!nvrs || nvrs.length === 0) {
          setBranches(MOCK_BRANCHES);
          setUsingMock(true);
          return;
        }

        const results = await Promise.allSettled(
          nvrs.map((nvr) => discoveryApi.getChannels(nvr.id))
        );
        if (cancelled) return;

        const nvrGroups = nvrs.map((nvr, i) => ({
          nvr,
          channels:
            results[i].status === "fulfilled"
              ? results[i].value.channels || []
              : [],
        }));

        const built = buildBranchesFromNvrs(nvrGroups);
        if (built.length === 0) {
          setBranches(MOCK_BRANCHES);
          setUsingMock(true);
        } else {
          setBranches(built);
          setUsingMock(false);
        }
      } catch {
        if (!cancelled) {
          setBranches(MOCK_BRANCHES);
          setUsingMock(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  // Filter branches + cameras by name
  const filtered = filter.trim()
    ? branches
        .map((b) => {
          const q = filter.toLowerCase();
          const camMatch = b.cameras.filter((c) =>
            c.name.toLowerCase().includes(q)
          );
          if (b.name.toLowerCase().includes(q)) return b;
          if (camMatch.length > 0) return { ...b, cameras: camMatch };
          return null;
        })
        .filter(Boolean)
    : branches;

  const handleSelectCamera = (cam) => {
    setSelectedId(cam.id);
    setSelectedCamera({
      id: cam.id,
      name: cam.name,
      online: cam.online,
      channel: cam.channel?.channel_id,
      ip: cam.channel?.ip_address,
      site: { name: cam.nvr?.code },
      nvr: { name: cam.nvr?.branch_name || cam.nvr?.nvr_ip },
    });
  };

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Header */}
      <div className="px-3 pt-4 pb-2 border-b border-gray-800/60 flex-shrink-0">
        <p className="text-[10px] font-semibold tracking-[0.15em] uppercase text-gray-600 mb-2">
          Branches
        </p>
        {/* Search */}
        <div className="relative">
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-600 pointer-events-none"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search branches, cameras…"
            className="
              w-full bg-gray-900/60 border border-gray-800 rounded
              pl-7 pr-3 py-1.5 text-xs text-gray-300
              placeholder-gray-600
              focus:outline-none focus:border-blue-600/50 focus:bg-gray-900
              transition-colors
            "
          />
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-2 px-1.5">
        {loading && (
          <div className="flex items-center justify-center mt-8">
            <span className="text-xs text-gray-600 animate-pulse">Loading…</span>
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <p className="text-center text-xs text-gray-600 mt-8 px-4">
            {filter ? "No results found" : "No branches available"}
          </p>
        )}

        {!loading &&
          filtered.map((branch, idx) => (
            <BranchRow
              key={branch.id}
              branch={branch}
              selectedId={selectedId}
              onSelect={handleSelectCamera}
              defaultOpen={idx === 0}
            />
          ))}
      </div>

      {/* Footer: mock data notice */}
      {usingMock && !loading && (
        <div className="px-3 py-2 border-t border-gray-800/60 flex-shrink-0">
          <p className="text-[10px] text-gray-700 text-center">
            Preview data — connect backend to load live branches
          </p>
        </div>
      )}
    </div>
  );
}
