import React, { useState } from "react";
import { useSitesStore } from "../store/sitesStore";
import { Play, RefreshCw, Video, Wifi, WifiOff } from "lucide-react";

// ─── Empty state ──────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 py-10">
      <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center mb-4">
        <Video className="w-6 h-6 text-gray-600" />
      </div>
      <p className="text-sm font-medium text-gray-500">No camera selected</p>
      <p className="text-xs text-gray-700 mt-1">
        Select a camera from the branch explorer to begin monitoring
      </p>
    </div>
  );
}

// ─── Metadata row ─────────────────────────────────────────────────────────────
function MetaRow({ label, value, highlight }) {
  return (
    <div className="flex items-baseline justify-between py-1 border-b border-gray-800/60 last:border-0">
      <span className="text-[11px] text-gray-600 uppercase tracking-wide flex-shrink-0 mr-3">
        {label}
      </span>
      <span className={`text-xs font-mono truncate ${highlight || "text-gray-300"}`}>
        {value || "—"}
      </span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function PreviewPanel() {
  const selectedCamera = useSitesStore((state) => state.selectedCamera);
  const previewState = useSitesStore((state) => state.previewState);
  const setPreviewState = useSitesStore((state) => state.setPreviewState);

  const [loading, setLoading] = useState(false);

  const handlePreviewClick = () => {
    if (!selectedCamera) return;
    setLoading(true);
    setTimeout(() => {
      setPreviewState({
        isPreviewing: true,
        streamUrl: "https://example.com/stream/" + selectedCamera.id,
      });
      setLoading(false);
    }, 800);
  };

  const handleRefreshClick = () => {
    if (!selectedCamera) return;
    setLoading(true);
    setTimeout(() => setLoading(false), 400);
  };

  if (!selectedCamera) {
    return (
      <div className="flex flex-col h-full bg-[#0d1117]">
        <EmptyState />
      </div>
    );
  }

  const { name, site, nvr, channel, ip, codec, bitrate, fps, resolution, lastSeen, online } =
    selectedCamera;

  return (
    <div className="flex flex-col h-full bg-[#0d1117] overflow-y-auto">
      {/* ── Top bar ── */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          {/* Online indicator */}
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              online ? "bg-emerald-400" : "bg-red-500/70"
            }`}
          />
          <span className="text-sm font-semibold text-white truncate">{name}</span>
          {site?.name && (
            <span className="text-xs text-gray-600 truncate hidden sm:block">
              / {site.name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0 ml-3">
          <button
            onClick={handlePreviewClick}
            disabled={loading || previewState.isPreviewing}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="w-3 h-3" />
            {loading ? "Loading…" : "Preview"}
          </button>
          <button
            onClick={handleRefreshClick}
            disabled={loading}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-200 disabled:opacity-40 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ── Preview window ── */}
      <div className="flex-shrink-0 px-4 pt-4">
        {/* Constrained container — max 640px wide, 16:9 aspect */}
        <div className="w-full max-w-[640px] mx-auto">
          {/* Label bar */}
          <div className="flex items-center justify-between bg-gray-900 border border-gray-700 border-b-0 rounded-t px-3 py-1.5">
            <div className="flex items-center gap-1.5">
              <Video className="w-3 h-3 text-gray-600" />
              <span className="text-[11px] text-gray-500 font-mono truncate max-w-[200px]">
                {name}
              </span>
            </div>
            <div className="flex items-center gap-1">
              {online ? (
                <Wifi className="w-3 h-3 text-emerald-500" />
              ) : (
                <WifiOff className="w-3 h-3 text-red-500/60" />
              )}
              <span
                className={`text-[10px] font-medium ${
                  online ? "text-emerald-500" : "text-red-500/60"
                }`}
              >
                {online ? "LIVE" : "OFFLINE"}
              </span>
            </div>
          </div>

          {/* 16:9 video area */}
          <div
            className="relative w-full bg-[#080c10] border border-gray-700 rounded-b overflow-hidden"
            style={{ paddingBottom: "56.25%" /* 16:9 */ }}
          >
            <div className="absolute inset-0 flex items-center justify-center">
              {previewState.isPreviewing ? (
                <div className="text-center">
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse mx-auto mb-2" />
                  <p className="text-xs text-gray-400 font-mono">LIVE STREAM</p>
                  <p className="text-[10px] text-gray-700 mt-1 font-mono truncate max-w-[200px] px-2">
                    {previewState.streamUrl}
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <Video className="w-8 h-8 text-gray-800 mx-auto mb-2" />
                  <p className="text-xs text-gray-700">Click Preview to load stream</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Metadata grid ── */}
      <div className="flex-shrink-0 px-4 pt-4 pb-4">
        <div className="w-full max-w-[640px] mx-auto">
          <p className="text-[10px] font-semibold tracking-[0.15em] uppercase text-gray-700 mb-2">
            Stream Info
          </p>
          <div className="bg-gray-900/40 border border-gray-800 rounded px-3 py-1">
            <div className="grid grid-cols-2 gap-x-6">
              <MetaRow label="NVR" value={nvr?.name} />
              <MetaRow label="Channel" value={channel} />
              <MetaRow label="IP" value={ip} />
              <MetaRow label="Codec" value={codec} />
              <MetaRow label="Resolution" value={resolution} />
              <MetaRow label="FPS" value={fps} />
              <MetaRow label="Bitrate" value={bitrate} />
              <MetaRow label="Last Seen" value={lastSeen} />
              <MetaRow
                label="Status"
                value={online ? "Online" : "Offline"}
                highlight={online ? "text-emerald-400" : "text-red-400"}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
