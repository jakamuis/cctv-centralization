import { useState, useEffect, useCallback } from "react";
import {
  Server, RefreshCw, Search, Monitor, Wifi, WifiOff,
  AlertTriangle, ShieldOff, Plus, Pencil, Trash2, Loader2,
} from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";
import { discoveryApi } from "../api";

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLE = {
  synced:      { cls: "bg-emerald-500/15 text-emerald-400", Icon: Wifi,          label: "Synced"      },
  unreachable: { cls: "bg-red-500/15 text-red-400",         Icon: WifiOff,       label: "Unreachable" },
  failed:      { cls: "bg-amber-500/15 text-amber-400",     Icon: AlertTriangle, label: "Failed"      },
  auth_error:  { cls: "bg-orange-500/15 text-orange-400",   Icon: ShieldOff,     label: "Auth Error"  },
};

function SyncBadge({ status }) {
  const s = STATUS_STYLE[status] || { cls: "bg-secondary text-muted-foreground", Icon: Server, label: status || "Unknown" };
  const { cls, Icon, label } = s;
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded ${cls}`}>
      <Icon size={10} className="flex-shrink-0" />
      {label}
    </span>
  );
}

function VendorBadge({ vendor }) {
  if (!vendor) return <span className="text-muted-foreground">—</span>;
  const map = {
    hikvision: "bg-blue-500/15 text-blue-400",
    acti_snvr: "bg-violet-500/15 text-violet-400",
    acti:      "bg-violet-500/15 text-violet-400",
  };
  return (
    <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${map[vendor?.toLowerCase()] || "bg-secondary text-muted-foreground"}`}>
      {vendor === "acti_snvr" ? "ACTi SNVR" : vendor}
    </span>
  );
}

function fmt(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" });
}

// ─── Form field ───────────────────────────────────────────────────────────────

function Field({ label, required, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

const inputCls = "bg-muted border border-border rounded px-2.5 py-1.5 text-xs text-foreground placeholder-muted-foreground outline-none focus:border-blue-500 transition-colors w-full";
const selectCls = `${inputCls} cursor-pointer`;

// ─── Add / Edit modal ─────────────────────────────────────────────────────────

const EMPTY_FORM = {
  branch_name: "", nvr_ip: "", http_port: "80", rtsp_port: "554",
  username: "", password: "", vendor: "hikvision", timezone: "WIB",
};

function NVRFormModal({ open, onClose, onSaved, editNvr }) {
  const isEdit = Boolean(editNvr);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setError(null);
      setSaving(false);
      if (isEdit) {
        setForm({
          branch_name: editNvr.branch_name || "",
          nvr_ip:      editNvr.nvr_ip      || "",
          http_port:   String(editNvr.http_port  ?? 80),
          rtsp_port:   String(editNvr.rtsp_port  ?? 554),
          username:    editNvr.username    || "",
          password:    "",
          vendor:      editNvr.vendor      || "hikvision",
          timezone:    editNvr.timezone    || "WIB",
        });
      } else {
        setForm(EMPTY_FORM);
      }
    }
  }, [open, editNvr, isEdit]);

  function set(key, val) {
    setForm(prev => ({ ...prev, [key]: val }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload = {
        branch_name: form.branch_name.trim(),
        nvr_ip:      form.nvr_ip.trim(),
        http_port:   parseInt(form.http_port, 10) || 80,
        rtsp_port:   parseInt(form.rtsp_port, 10) || 554,
        username:    form.username.trim(),
        vendor:      form.vendor,
        timezone:    form.timezone,
      };
      if (form.password) payload.password = form.password;

      if (isEdit) {
        await discoveryApi.updateNvr(editNvr.id, payload);
      } else {
        if (!form.password) throw new Error("Password is required for new devices.");
        payload.password = form.password;
        await discoveryApi.addNvr(payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Device" : "Add Device"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3 pt-1">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Branch Name" required>
              <input className={inputCls} value={form.branch_name}
                onChange={e => set("branch_name", e.target.value)}
                placeholder="Branch 01" required />
            </Field>
            <Field label="NVR IP" required>
              <input className={inputCls} value={form.nvr_ip}
                onChange={e => set("nvr_ip", e.target.value)}
                placeholder="192.168.1.1" required />
            </Field>
            <Field label="HTTP Port">
              <input className={inputCls} type="number" value={form.http_port}
                onChange={e => set("http_port", e.target.value)}
                placeholder="80" min={1} max={65535} />
            </Field>
            <Field label="RTSP Port">
              <input className={inputCls} type="number" value={form.rtsp_port}
                onChange={e => set("rtsp_port", e.target.value)}
                placeholder="554" min={1} max={65535} />
            </Field>
            <Field label="Username" required>
              <input className={inputCls} value={form.username}
                onChange={e => set("username", e.target.value)}
                placeholder="admin" required autoComplete="username" />
            </Field>
            <Field label={isEdit ? "Password (leave blank to keep)" : "Password"} required={!isEdit}>
              <input className={inputCls} type="password" value={form.password}
                onChange={e => set("password", e.target.value)}
                placeholder={isEdit ? "••••••••" : "Enter password"}
                required={!isEdit} autoComplete="new-password" />
            </Field>
            <Field label="Vendor">
              <select className={selectCls} value={form.vendor}
                onChange={e => set("vendor", e.target.value)}>
                <option value="hikvision">Hikvision</option>
                <option value="acti_snvr">ACTi SNVR</option>
              </select>
            </Field>
            <Field label="Timezone">
              <select className={selectCls} value={form.timezone}
                onChange={e => set("timezone", e.target.value)}>
                <option value="WIB">WIB (UTC+7)</option>
                <option value="WITA">WITA (UTC+8)</option>
                <option value="WIT">WIT (UTC+9)</option>
              </select>
            </Field>
          </div>

          {error && (
            <p className="text-[11px] text-red-400 bg-red-500/10 px-2.5 py-1.5 rounded">{error}</p>
          )}

          <DialogFooter>
            <button type="button" onClick={onClose}
              className="px-3 py-1.5 text-xs rounded border border-border text-muted-foreground hover:bg-secondary transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50">
              {saving && <Loader2 size={11} className="animate-spin" />}
              {isEdit ? "Save Changes" : "Add & Probe"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Delete confirm modal ─────────────────────────────────────────────────────

function DeleteModal({ nvr, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await discoveryApi.deleteNvr(nvr.id);
      onDeleted();
      onClose();
    } catch (err) {
      setError(err.message || "Delete failed.");
      setDeleting(false);
    }
  }

  return (
    <Dialog open={Boolean(nvr)} onOpenChange={v => { if (!v) onClose(); }}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Delete Device</DialogTitle>
        </DialogHeader>
        <p className="text-xs text-muted-foreground mt-1">
          This will permanently remove{" "}
          <span className="text-foreground font-medium">
            {nvr?.branch_name || nvr?.code}
          </span>{" "}
          ({nvr?.nvr_ip}) and all its channels. This cannot be undone.
        </p>
        {error && (
          <p className="text-[11px] text-red-400 bg-red-500/10 px-2.5 py-1.5 rounded">{error}</p>
        )}
        <DialogFooter>
          <button onClick={onClose}
            className="px-3 py-1.5 text-xs rounded border border-border text-muted-foreground hover:bg-secondary transition-colors">
            Cancel
          </button>
          <button onClick={handleDelete} disabled={deleting}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-red-600 hover:bg-red-500 text-white transition-colors disabled:opacity-50">
            {deleting && <Loader2 size={11} className="animate-spin" />}
            Delete
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Devices Page ─────────────────────────────────────────────────────────────

export default function DevicesPage() {
  const [nvrs,     setNvrs]     = useState([]);
  const [channels, setChannels] = useState({});
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [search,   setSearch]   = useState("");

  // modal state
  const [formOpen,  setFormOpen]  = useState(false);
  const [editNvr,   setEditNvr]   = useState(null);  // null = add mode, NVR obj = edit mode
  const [deleteNvr, setDeleteNvr] = useState(null);  // NVR to delete (or null)
  const [syncing,   setSyncing]   = useState(false);
  const [syncingRow, setSyncingRow] = useState(null); // nvr.id being synced

  async function handleSyncOne(nvr) {
    setSyncingRow(nvr.id);
    try {
      await discoveryApi.addNvr({
        nvr_ip:      nvr.nvr_ip,
        http_port:   nvr.http_port,
        rtsp_port:   nvr.rtsp_port,
        username:    nvr.username,
        vendor:      nvr.vendor,
        code:        nvr.code,
        branch_name: nvr.branch_name,
      });
      await load();
    } finally {
      setSyncingRow(null);
    }
  }

  async function handleSyncAll() {
    setSyncing(true);
    try {
      await discoveryApi.syncAll();
      await load();
    } finally {
      setSyncing(false);
    }
  }

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await discoveryApi.getNvrs();
      const list = Array.isArray(data) ? data : [];
      setNvrs(list);

      const results = await Promise.allSettled(
        list.map(nvr => discoveryApi.getChannels(nvr.id))
      );
      const counts = {};
      list.forEach((nvr, i) => {
        if (results[i].status === "fulfilled") {
          counts[nvr.id] = results[i].value?.channel_count ?? results[i].value?.channels?.length ?? 0;
        } else {
          counts[nvr.id] = 0;
        }
      });
      setChannels(counts);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = nvrs.filter(n =>
    search === "" ||
    [n.branch_name, n.nvr_ip, n.vendor, n.code, n.model, n.device_name]
      .filter(Boolean)
      .some(v => v.toLowerCase().includes(search.toLowerCase()))
  );

  const synced    = nvrs.filter(n => n.sync_status === "synced").length;
  const offline   = nvrs.length - synced;
  const totalCams = Object.values(channels).reduce((a, b) => a + b, 0);

  const HEADS = ["Name / Branch", "IP Address", "Vendor", "Status", "Channels", "Model", "Last Synced", "Error", "Actions"];

  return (
    <div className="flex-1 flex flex-col bg-background min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card flex-shrink-0">
        <div className="flex items-center gap-3">
          <Server size={16} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Devices</span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] bg-secondary text-muted-foreground px-1.5 py-0.5 rounded">{nvrs.length} NVRs</span>
            <span className="text-[10px] bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded">{synced} online</span>
            <span className="text-[10px] bg-red-500/15 text-red-400 px-1.5 py-0.5 rounded">{offline} offline</span>
            <span className="text-[10px] bg-blue-500/15 text-blue-400 px-1.5 py-0.5 rounded">{totalCams} cameras</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 bg-muted border border-border rounded px-2.5 py-1.5 w-56">
            <Search size={12} className="text-muted-foreground flex-shrink-0" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search NVRs…"
              className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
            />
          </div>
          <button
            onClick={load}
            title="Refresh"
            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={handleSyncAll}
            disabled={syncing || loading}
            title="Sync all NVRs"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50"
          >
            {syncing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            {syncing ? "Syncing…" : "Sync All"}
          </button>
          <button
            onClick={() => { setEditNvr(null); setFormOpen(true); }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-blue-600 hover:bg-blue-500 text-white transition-colors"
          >
            <Plus size={12} />
            Add Device
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading && (
          <div className="flex items-center justify-center h-40 text-xs text-muted-foreground">
            Loading devices…
          </div>
        )}
        {!loading && error && (
          <div className="flex items-center justify-center h-40 text-xs text-red-400">{error}</div>
        )}
        {!loading && !error && (
          <Table>
            <TableHeader>
              <TableRow className="border-border">
                {HEADS.map(h => (
                  <TableHead key={h} className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide py-2.5 px-3 bg-card whitespace-nowrap">
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={HEADS.length} className="text-center text-xs text-muted-foreground py-12">
                    {search ? "No NVRs match your search." : "No devices found."}
                  </TableCell>
                </TableRow>
              ) : filtered.map(nvr => (
                <TableRow key={nvr.id} className="border-border hover:bg-secondary/20">
                  {/* Name */}
                  <TableCell className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Monitor size={13} className={`flex-shrink-0 ${nvr.sync_status === "synced" ? "text-emerald-400" : "text-muted-foreground"}`} />
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-foreground truncate max-w-[160px]">
                          {nvr.branch_name || nvr.device_name || nvr.code}
                        </p>
                        <p className="text-[10px] text-muted-foreground font-mono">{nvr.code}</p>
                      </div>
                    </div>
                  </TableCell>
                  {/* IP */}
                  <TableCell className="px-3 py-2 text-xs font-mono text-foreground">{nvr.nvr_ip || "—"}</TableCell>
                  {/* Vendor */}
                  <TableCell className="px-3 py-2"><VendorBadge vendor={nvr.vendor} /></TableCell>
                  {/* Status */}
                  <TableCell className="px-3 py-2"><SyncBadge status={nvr.sync_status} /></TableCell>
                  {/* Channels */}
                  <TableCell className="px-3 py-2">
                    <span className={`text-xs font-medium ${channels[nvr.id] > 0 ? "text-foreground" : "text-muted-foreground"}`}>
                      {channels[nvr.id] !== undefined ? channels[nvr.id] : "—"}
                    </span>
                  </TableCell>
                  {/* Model */}
                  <TableCell className="px-3 py-2 text-xs text-muted-foreground max-w-[140px] truncate">
                    {nvr.model || nvr.device_name || "—"}
                  </TableCell>
                  {/* Last Synced */}
                  <TableCell className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
                    {fmt(nvr.last_synced_at)}
                  </TableCell>
                  {/* Error */}
                  <TableCell className="px-3 py-2 max-w-[220px]">
                    {nvr.sync_error ? (
                      <span className="text-[11px] text-amber-400 truncate block" title={nvr.sync_error}>
                        {nvr.sync_error.slice(0, 60)}{nvr.sync_error.length > 60 ? "…" : ""}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  {/* Actions */}
                  <TableCell className="px-3 py-2">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleSyncOne(nvr)}
                        disabled={syncingRow === nvr.id}
                        title="Sync this device"
                        className="p-1 rounded hover:bg-emerald-500/15 text-muted-foreground hover:text-emerald-400 transition-colors disabled:opacity-50"
                      >
                        {syncingRow === nvr.id
                          ? <Loader2 size={12} className="animate-spin" />
                          : <RefreshCw size={12} />}
                      </button>
                      <button
                        onClick={() => { setEditNvr(nvr); setFormOpen(true); }}
                        title="Edit"
                        className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <Pencil size={12} />
                      </button>
                      <button
                        onClick={() => setDeleteNvr(nvr)}
                        title="Delete"
                        className="p-1 rounded hover:bg-red-500/15 text-muted-foreground hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Add / Edit modal */}
      <NVRFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSaved={load}
        editNvr={editNvr}
      />

      {/* Delete confirm modal */}
      {deleteNvr && (
        <DeleteModal
          nvr={deleteNvr}
          onClose={() => setDeleteNvr(null)}
          onDeleted={load}
        />
      )}
    </div>
  );
}
