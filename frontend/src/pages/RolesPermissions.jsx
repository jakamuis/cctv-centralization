import { useState, useEffect, useCallback } from "react";
import { ShieldCheck, RefreshCw, Key } from "lucide-react";
import { rolesApi } from "../api";

export default function RolesPermissionsPage() {
  const [roles,       setRoles]       = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    Promise.all([rolesApi.list(), rolesApi.listPermissions()])
      .then(([r, p]) => {
        setRoles(Array.isArray(r) ? r : []);
        setPermissions(Array.isArray(p) ? p : []);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const ROLE_COLOR = {
    SUPER_ADMIN: { border: "border-red-500/30",    bg: "bg-red-500/10",    badge: "bg-red-500/15 text-red-400" },
    OPERATOR:    { border: "border-blue-500/30",   bg: "bg-blue-500/10",   badge: "bg-blue-500/15 text-blue-400" },
    VIEWER:      { border: "border-secondary",     bg: "bg-secondary/50",  badge: "bg-secondary text-muted-foreground" },
  };

  return (
    <div className="flex-1 flex flex-col bg-background min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <ShieldCheck size={16} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Roles & Permissions</span>
        </div>
        <button onClick={load} className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-auto p-5 space-y-5">
        {loading && <div className="flex items-center justify-center h-40 text-xs text-muted-foreground">Loading…</div>}
        {!loading && error && <div className="flex items-center justify-center h-40 text-xs text-red-400">{error}</div>}

        {!loading && !error && (
          <>
            {/* Roles cards */}
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Roles</h2>
              <div className="grid grid-cols-3 gap-3">
                {roles.map(role => {
                  const c = ROLE_COLOR[role.name] || ROLE_COLOR.VIEWER;
                  const rolePerms = role.permissions || [];
                  return (
                    <div key={role.id} className={`rounded-lg border ${c.border} ${c.bg} p-4`}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <ShieldCheck size={14} className="text-muted-foreground" />
                          <span className="text-xs font-semibold text-foreground">{role.name}</span>
                        </div>
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${c.badge}`}>
                          {rolePerms.length} perms
                        </span>
                      </div>
                      {role.description && (
                        <p className="text-[11px] text-muted-foreground mb-3 leading-relaxed">{role.description}</p>
                      )}
                      <div className="space-y-1">
                        {rolePerms.length === 0 ? (
                          <p className="text-[11px] text-muted-foreground italic">No permissions assigned</p>
                        ) : rolePerms.map(p => (
                          <div key={p.id} className="flex items-center gap-1.5">
                            <Key size={9} className="text-muted-foreground flex-shrink-0" />
                            <span className="text-[11px] text-foreground font-mono">{p.code}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {roles.length === 0 && (
                  <div className="col-span-3 text-center text-xs text-muted-foreground py-10">No roles found.</div>
                )}
              </div>
            </div>

            {/* All permissions */}
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                All Permissions <span className="text-muted-foreground font-normal normal-case">({permissions.length})</span>
              </h2>
              <div className="bg-card border border-border rounded-lg divide-y divide-border">
                {permissions.length === 0 ? (
                  <div className="text-center text-xs text-muted-foreground py-8">No permissions found.</div>
                ) : permissions.map(p => (
                  <div key={p.id} className="flex items-center justify-between px-4 py-2.5">
                    <div className="flex items-center gap-2.5">
                      <Key size={12} className="text-muted-foreground flex-shrink-0" />
                      <span className="text-xs font-mono text-foreground">{p.code}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{p.description || "—"}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
