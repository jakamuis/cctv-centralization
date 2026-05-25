import React from "react";

export default function SidebarBrand({ collapsed }) {
  return (
    <div
      className={`
        flex flex-col items-center justify-center select-none
        border-b border-gray-700/60
        ${collapsed ? "h-14 px-2" : "h-20 px-4 py-3"}
      `}
    >
      {/* Icon mark */}
      <div className="flex items-center justify-center w-8 h-8 rounded-sm bg-blue-600 flex-shrink-0">
        <svg
          className="w-5 h-5 text-white"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {/* Camera lens / monitoring icon */}
          <circle cx="12" cy="12" r="3" />
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
        </svg>
      </div>

      {!collapsed && (
        <div className="mt-2 text-center leading-none">
          <span className="block text-white font-bold text-sm tracking-[0.18em] uppercase">
            SAMATOR
          </span>
          <span className="block text-gray-500 text-[9px] tracking-widest uppercase mt-0.5">
            Security Monitoring
          </span>
        </div>
      )}
    </div>
  );
}
