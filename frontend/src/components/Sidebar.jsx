import React, { useState } from "react";
import SidebarBrand from "./SidebarBrand";
import { Home, GitBranch, Cpu, Video, Play, Bell, Settings } from "lucide-react";

const menuItems = [
  { label: "Dashboard", icon: Home },
  { label: "Branches", icon: GitBranch },
  { label: "Devices", icon: Cpu },
  { label: "Cameras", icon: Video },
  { label: "Playback", icon: Play },
  { label: "Alerts", icon: Bell },
  { label: "Settings", icon: Settings },
];

export default function Sidebar({ activeItem, onNavigate }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`
        flex flex-col bg-[#0d1117] border-r border-gray-800 text-gray-400
        ${collapsed ? "w-14" : "w-44"}
        transition-all duration-300 ease-in-out
        sticky top-0 h-screen flex-shrink-0
      `}
    >
      <SidebarBrand collapsed={collapsed} />

      <nav className="flex-1 overflow-y-auto py-3 px-1.5">
        <ul className="space-y-0.5">
          {menuItems.map(({ label, icon: Icon }) => {
            const isActive = activeItem === label;
            return (
              <li key={label}>
                <button
                  onClick={() => onNavigate?.(label)}
                  className={`
                    flex items-center w-full px-2.5 py-2 text-xs font-medium rounded
                    transition-colors duration-150
                    ${
                      isActive
                        ? "bg-blue-600/20 text-blue-400 border-l-2 border-blue-500"
                        : "text-gray-400 hover:bg-gray-800/70 hover:text-gray-200 border-l-2 border-transparent"
                    }
                  `}
                  title={collapsed ? label : undefined}
                >
                  <Icon
                    className={`flex-shrink-0 ${collapsed ? "w-4 h-4" : "w-4 h-4"} ${
                      isActive ? "text-blue-400" : "text-gray-500"
                    }`}
                  />
                  {!collapsed && (
                    <span className="ml-2.5 truncate">{label}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <div className="px-1.5 pb-3 border-t border-gray-800 pt-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 hover:bg-gray-800 rounded transition-colors text-gray-600 hover:text-gray-400"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
          ) : (
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M15 18l-6-6 6-6" />
            </svg>
          )}
        </button>
      </div>
    </aside>
  );
}
