import { useState, useEffect, useCallback } from "react";
import { Bell, RefreshCw, Search, CheckCheck, XCircle } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from "../components/ui/table";
import { alertsApi } from "../api";

const SEVERITY_STYLE = {
  critical: "bg-red-500/15 text-red-400",
  high:     "bg-orange-500/15 text-orange-400",
  medium:   "bg-amber-500/15 text-amber-400",
  low:      "bg-blue-500/15 text-blue-400",
};

function SeverityBadge({ severity }) {
  const s = (severity || "").toLowerCase();
  return (
    <span className={`text-[11px] font-medium px-2 py-0.5 rounded capitalize ${SEVERITY_STYLE[s] || "bg-muted text-muted-foreground"}`}>
      {severity || "—"}
    </span>
  );
}

function StatusBadge({ active, acknowledged }) {
  if (!active)        return <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-secondary text-muted-foreground">Resolved</span>;
  if (acknowledged)   return <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-blue-500/15 text-blue-400">Acknowledged</span>;
  return <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-red-500/15 text-red-400">Active</span>;
}

function fmt(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" });
}

export default function AlertsPage() {
  const [alerts,  setAlerts]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [search,  setSearch]  = useState("");
  const [working, setWorking] = useState({}); // id → "ack"|"resolve"

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    alertsApi.list()
      .then(d => setAlerts(d.items || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = alerts.filter(a =>
    search === "" ||
    [a.alert_type, a.severity, a.message]
      .filter(Boolean)
      .some(v => v.toLowerCase().includes(search.toLowerCase()))
  );

  async function act(id, action) {
    setWorking(w => ({ ...w, [id]: action }));
    try {
      if (action === "ack")    await alertsApi.acknowledge(id);
      if (action === "resolve") await alertsApi.resolve(id);
      load();
    } catch {}
    finally { setWorking(w => { const n = { ...w }; delete n[id]; return n; }); }
  }

  const TABLE_HEADS = ["Severity", "Type", "Message", "Device", "Status", "Created", "Actions"];

  return (
    <div className="flex-1 flex flex-col bg-background min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <Bell size={16} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Alerts</span>
          <span className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">{alerts.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 bg-muted border border-border rounded px-2.5 py-1.5 w-52">
            <Search size={12} className="text-muted-foreground flex-shrink-0" />
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search alerts…"
              className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
            />
          </div>
          <button onClick={load} className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading && <div className="flex items-center justify-center h-40 text-xs text-muted-foreground">Loading…</div>}
        {!loading && error && <div className="flex items-center justify-center h-40 text-xs text-red-400">{error}</div>}
        {!loading && !error && (
          <Table>
            <TableHeader>
              <TableRow className="border-border">
                {TABLE_HEADS.map(h => (
                  <TableHead key={h} className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide py-2.5 px-3 bg-card">{h}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={TABLE_HEADS.length} className="text-center text-xs text-muted-foreground py-12">
                    {search ? "No matches." : "No alerts found."}
                  </TableCell>
                </TableRow>
              ) : filtered.map(a => (
                <TableRow key={a.id} className="border-border hover:bg-secondary/20">
                  <TableCell className="px-3 py-2"><SeverityBadge severity={a.severity} /></TableCell>
                  <TableCell className="px-3 py-2 text-xs text-foreground">{a.alert_type || "—"}</TableCell>
                  <TableCell className="px-3 py-2 text-xs text-foreground max-w-[260px] truncate">{a.message || "—"}</TableCell>
                  <TableCell className="px-3 py-2 text-xs font-mono text-muted-foreground max-w-[110px] truncate" title={a.device_id}>
                    {a.device_id ? a.device_id.slice(0, 8) + "…" : "—"}
                  </TableCell>
                  <TableCell className="px-3 py-2"><StatusBadge active={a.active} acknowledged={a.acknowledged} /></TableCell>
                  <TableCell className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">{fmt(a.created_at)}</TableCell>
                  <TableCell className="px-3 py-2">
                    <div className="flex items-center gap-1">
                      {a.active && !a.acknowledged && (
                        <button
                          onClick={() => act(a.id, "ack")}
                          disabled={!!working[a.id]}
                          title="Acknowledge"
                          className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 hover:bg-blue-500/25 disabled:opacity-50 transition-colors"
                        >
                          <CheckCheck size={11} />
                          {working[a.id] === "ack" ? "…" : "Ack"}
                        </button>
                      )}
                      {a.active && (
                        <button
                          onClick={() => act(a.id, "resolve")}
                          disabled={!!working[a.id]}
                          title="Resolve"
                          className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25 disabled:opacity-50 transition-colors"
                        >
                          <XCircle size={11} />
                          {working[a.id] === "resolve" ? "…" : "Resolve"}
                        </button>
                      )}
                      {!a.active && <span className="text-[11px] text-muted-foreground">Closed</span>}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
