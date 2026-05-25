import React from "react";
import Sidebar from "./Sidebar";
import CameraDetailPanel from "./CameraDetailPanel";
import PreviewPanel from "./PreviewPanel";
import SitesExplorer from "./SitesExplorer";

export default function AppLayout() {
  // Wrap existing layout with template's SidebarProvider structure where possible
  // so we can progressively adopt the template sidebar behaviour.
  return (
    <div className="flex h-screen bg-[#0d1117] text-gray-300 font-sans overflow-hidden">
      {/* Left Sidebar — icon nav */}
      <Sidebar />

      {/* Main content area */}
      <main className="flex flex-1 overflow-hidden min-w-0">
        {/* Column 1: Branch / Camera Explorer — narrow tree */}
        <div className="w-56 border-r border-gray-800 overflow-y-auto flex-shrink-0">
          <SitesExplorer />
        </div>

        {/* Column 2: Camera Detail Panel — fixed info panel */}
        <div className="w-72 border-r border-gray-800 overflow-y-auto flex-shrink-0">
          <CameraDetailPanel />
        </div>

        {/* Column 3: Preview + metadata — scrollable, NOT full-height stretch */}
        <div className="flex-1 overflow-y-auto min-w-0 bg-[#0d1117]">
          <PreviewPanel />
        </div>
      </main>
    </div>
  );
}
