import React, { useState } from "react";
import { useSitesStore } from "../store/sitesStore";
import { RefreshCw, Play, Eye, Video } from "lucide-react";

const tabs = ["Overview", "Stream", "Events"];

// ─── Info row ─────────────────────────────────────────────────────────────────
function InfoRow({ label, value, highlight }) {
  return (
    <div className="flex items-baseline justify-between py-1 border-b border-gray-800/50 last:border-0">
      <span className="text-[11px] text-gray-600 uppercase tracking-wide flex-shrink-0 mr-2 w-24">
        {label}
      </span>
      <span className={`text-xs font-mono truncate text-right ${highlight || "text-gray-300"}`}>
        {value || "—"}
      </span>
    </div>
  );
}

export default function CameraDetailPanel() {
  const selectedCamera = useSitesStore((state) => state.selectedCamera);
  const [activeTab, setActiveTab] = useState("Overview");

  if (!selectedCamera) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-4 text-center">
        <Video className="w-8 h-8 text-gray-800 mb-3" />
        <p className="text-xs text-gray-600">Select a camera to see details</p>
      </div>
    );
  }

  const {
    name, site, nvr, channel, ip,
    codec, bitrate, fps, resolution,
    lastOnline, streamType, online,
  } = selectedCamera;

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* ── Header ── */}
      <div className="px-3 pt-3 pb-2 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              online ? "bg-emerald-400" : "bg-red-500/70"
            }`}
          />
          <h2 className="text-sm font-semibold text-white truncate">{name}</h2>
        </div>
        <p className="text-[11px] text-gray-600 pl-4 truncate">
          {site?.name || "Unknown Site"}
          {nvr?.name ? ` · ${nvr.name}` : ""}
        </p>
      </div>

      {/* ── Action buttons ── */}
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-gray-800 flex-shrink-0">
        <button className="flex items-center gap-1 px-2 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:border-blue-600/60 hover:text-blue-400 transition-colors">
          <Eye className="w-3 h-3" />
          Preview
        </button>
        <button className="flex items-center gap-1 px-2 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:border-blue-600/60 hover:text-blue-400 transition-colors">
          <Play className="w-3 h-3" />
          Playback
        </button>
        <button className="flex items-center gap-1 px-2 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-200 transition-colors ml-auto">
          <RefreshCw className="w-3 h-3" />
        </button>
      </div>

      {/* ── Tabs ── */}
      <div className="flex border-b border-gray-800 flex-shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`
              flex-1 py-1.5 text-xs font-medium transition-colors
              ${
                activeTab === tab
                  ? "text-blue-400 border-b-2 border-blue-500 -mb-px"
                  : "text-gray-600 hover:text-gray-300"
              }
            `}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {activeTab === "Overview" && (
          <div>
            <p className="text-[10px] font-semibold tracking-[0.15em] uppercase text-gray-700 mb-1.5">
              Identity
            </p>
            <div className="mb-3">
              <InfoRow label="Camera" value={name} />
              <InfoRow label="Site" value={site?.name} />
              <InfoRow label="NVR" value={nvr?.name} />
              <InfoRow label="Channel" value={channel} />
              <InfoRow label="IP" value={ip} />
            </div>

            <p className="text-[10px] font-semibold tracking-[0.15em] uppercase text-gray-700 mb-1.5">
              Stream
            </p>
            <div className="mb-3">
              <InfoRow label="Codec" value={codec} />
              <InfoRow label="Resolution" value={resolution} />
              <InfoRow label="FPS" value={fps} />
              <InfoRow label="Bitrate" value={bitrate} />
              <InfoRow label="Type" value={streamType} />
            </div>

            <p className="text-[10px] font-semibold tracking-[0.15em] uppercase text-gray-700 mb-1.5">
              Status
            </p>
            <div>
              <InfoRow
                label="Online"
                value={online ? "Online" : "Offline"}
                highlight={online ? "text-emerald-400" : "text-red-400"}
              />
              <InfoRow label="Last Online" value={lastOnline} />
            </div>
          </div>
        )}

        {activeTab === "Stream" && (
          <div className="text-xs text-gray-600 mt-4 text-center">
            Stream configuration coming soon
          </div>
        )}

        {activeTab === "Events" && (
          <div className="text-xs text-gray-600 mt-4 text-center">
            Event log coming soon
          </div>
        )}
      </div>
    </div>
  );
}
