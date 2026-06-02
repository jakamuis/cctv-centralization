import { useState, useEffect, useCallback } from "react";
import { Plus, Server, Pencil, Trash2, X, RefreshCw, Search } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "../components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { devicesApi } from "../api";

const DEVICE_TYPES   = ["NVR", "CAMERA", "ENCODER", "DECODER", "SWITCH", "SERVER"];
const DEVICE_STATUSES = ["ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN", "MAINTENANCE"];

const EMPTY_FORM = {
  device_type:               "NVR",
  vendor:                    "",
  model:                     "",
  serial_number:             "",
  firmware_version:          "",
  ip_address:                "",
  port:                      "",
  username:                  "",
  password:                  "",
  mac_address:               "",
  site_id:                   "",
  status:                    "UNKNOWN",
  heartbeat_interval_seconds: 30,
  offline_threshold_seconds:  120,
};

const STATUS_STYLE = {
  ONLINE:      "bg-emerald-500/15 text-emerald-400",
  OFFLINE:     "bg-red-500/15 text-red-400",
  DEGRADED:    "bg-amber-500/15 text-amber-400",
  MAINTENANCE: "bg-blue-500/15 text-blue-400",
  UNKNOWN:     "bg-muted text-muted-foreground",
};

function StatusBadge({ status }) {
  return (
    <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${STATUS_STYLE[status] || STATUS_STYLE.UNKNOWN}`}>
      {status || "—"}
    </span>
  );
}

const inputCls  = "w-full bg-muted border border-border rounded px-2.5 py-1.5 text-xs text-foreground placeholder-muted-foreground outline-none focus:border-primary/50 transition-colors";
const selectCls = `${inputCls} cursor-pointer`;

function FormField({ label, required, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

// ─── Add / Edit Drawer ────────────────────────────────────────────────────────

function DeviceDrawer({ open, onOpenChange, editTarget, onSaved }) {
  const [form, setForm]           = useState(EMPTY_FORM);
  const [saving, setSaving]       = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setSaveError(null);
    if (editTarget) {
      setForm({
        device_type:               editTarget.device_type  || "NVR",
        vendor:                    editTarget.vendor        || "",
        model:                     editTarget.model         || "",
        serial_number:             editTarget.serial_number || "",
        firmware_version:          editTarget.firmware_version || "",
        ip_address:                editTarget.ip_address    || "",
        port:                      editTarget.port          ?? "",
        username:                  editTarget.username      || "",
        password:                  "",
        mac_address:               editTarget.mac_address   || "",
        site_id:                   editTarget.site_id       || "",
        status:                    editTarget.status        || "UNKNOWN",
        heartbeat_interval_seconds: editTarget.heartbeat_interval_seconds ?? 30,
        offline_threshold_seconds:  editTarget.offline_threshold_seconds  ?? 120,
      });
    } else {
      setForm(EMPTY_FORM);
    }
  }, [open, editTarget]);

  function set(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      const payload = {
        device_type:               form.device_type,
        vendor:                    form.vendor    || null,
        model:                     form.model     || null,
        serial_number:             form.serial_number    || null,
        firmware_version:          form.firmware_version || null,
        ip_address:                form.ip_address || null,
        port:                      form.port !== "" ? Number(form.port) : null,
        username:                  form.username  || null,
        mac_address:               form.mac_address || null,
        site_id:                   form.site_id   || null,
        status:                    form.status,
        heartbeat_interval_seconds: Number(form.heartbeat_interval_seconds) || 30,
        offline_threshold_seconds:  Number(form.offline_threshold_seconds)  || 120,
      };
      if (form.password) payload.encrypted_password = form.password;

      if (editTarget) {
        await devicesApi.update(editTarget.id, payload);
      } else {
        await devicesApi.create(payload);
      }

      onOpenChange(false);
      onSaved();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[480px] sm:max-w-[480px] bg-card border-l border-border flex flex-col p-0 gap-0"
      >
        <SheetHeader className="px-5 py-4 border-b border-border">
          <SheetTitle className="text-sm font-semibold">
            {editTarget ? "Edit Device" : "Add Device"}
          </SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3.5">
          {/* Type + Status */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Device Type" required>
              <select
                value={form.device_type}
                onChange={(e) => set("device_type", e.target.value)}
                className={selectCls}
              >
                {DEVICE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
            <FormField label="Status" required>
              <select
                value={form.status}
                onChange={(e) => set("status", e.target.value)}
                className={selectCls}
              >
                {DEVICE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </FormField>
          </div>

          {/* Vendor + Model */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Vendor">
              <input
                value={form.vendor}
                onChange={(e) => set("vendor", e.target.value)}
                placeholder="e.g. Hikvision"
                className={inputCls}
              />
            </FormField>
            <FormField label="Model">
              <input
                value={form.model}
                onChange={(e) => set("model", e.target.value)}
                placeholder="e.g. DS-7616NI"
                className={inputCls}
              />
            </FormField>
          </div>

          {/* IP + Port */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="IP Address">
              <input
                value={form.ip_address}
                onChange={(e) => set("ip_address", e.target.value)}
                placeholder="192.168.1.100"
                className={inputCls}
              />
            </FormField>
            <FormField label="Port">
              <input
                type="number"
                value={form.port}
                onChange={(e) => set("port", e.target.value)}
                placeholder="80"
                className={inputCls}
              />
            </FormField>
          </div>

          {/* Username + Password */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Username">
              <input
                value={form.username}
                onChange={(e) => set("username", e.target.value)}
                placeholder="admin"
                className={inputCls}
              />
            </FormField>
            <FormField label={editTarget ? "Password (blank = unchanged)" : "Password"}>
              <input
                type="password"
                value={form.password}
                onChange={(e) => set("password", e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </FormField>
          </div>

          {/* Serial + Firmware */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Serial Number">
              <input
                value={form.serial_number}
                onChange={(e) => set("serial_number", e.target.value)}
                placeholder="SN12345678"
                className={inputCls}
              />
            </FormField>
            <FormField label="Firmware Version">
              <input
                value={form.firmware_version}
                onChange={(e) => set("firmware_version", e.target.value)}
                placeholder="V4.12.0"
                className={inputCls}
              />
            </FormField>
          </div>

          {/* MAC + Site ID */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="MAC Address">
              <input
                value={form.mac_address}
                onChange={(e) => set("mac_address", e.target.value)}
                placeholder="AA:BB:CC:DD:EE:FF"
                className={inputCls}
              />
            </FormField>
            <FormField label="Site ID">
              <input
                value={form.site_id}
                onChange={(e) => set("site_id", e.target.value)}
                placeholder="UUID"
                className={inputCls}
              />
            </FormField>
          </div>

          {/* Heartbeat + Offline threshold */}
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Heartbeat Interval (s)">
              <input
                type="number"
                value={form.heartbeat_interval_seconds}
                onChange={(e) => set("heartbeat_interval_seconds", e.target.value)}
                className={inputCls}
              />
            </FormField>
            <FormField label="Offline Threshold (s)">
              <input
                type="number"
                value={form.offline_threshold_seconds}
                onChange={(e) => set("offline_threshold_seconds", e.target.value)}
                className={inputCls}
              />
            </FormField>
          </div>

          {saveError && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2 leading-relaxed">
              {saveError}
            </p>
          )}
        </div>

        <SheetFooter className="flex flex-row gap-2 px-5 py-4 border-t border-border">
          <button
            onClick={() => onOpenChange(false)}
            className="flex-1 px-3 py-2 rounded border border-border text-xs text-foreground hover:bg-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 px-3 py-2 rounded bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium transition-colors"
          >
            {saving ? "Saving…" : editTarget ? "Save Changes" : "Add Device"}
          </button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

// ─── Devices Page ─────────────────────────────────────────────────────────────

export default function DevicesPage() {
  const [devices,       setDevices]       = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(null);
  const [search,        setSearch]        = useState("");
  const [drawerOpen,    setDrawerOpen]    = useState(false);
  const [editTarget,    setEditTarget]    = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const loadDevices = useCallback(() => {
    setLoading(true);
    setError(null);
    devicesApi
      .list()
      .then((data) => setDevices(data.items || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadDevices(); }, [loadDevices]);

  const filtered = devices.filter((d) =>
    search === "" ||
    [d.vendor, d.model, d.ip_address, d.device_type, d.serial_number, d.username]
      .filter(Boolean)
      .some((v) => v.toLowerCase().includes(search.toLowerCase()))
  );

  function openAdd() {
    setEditTarget(null);
    setDrawerOpen(true);
  }

  function openEdit(device) {
    setEditTarget(device);
    setDrawerOpen(true);
  }

  async function handleDelete(id) {
    try {
      await devicesApi.remove(id);
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setDeleteConfirm(null);
      loadDevices();
    }
  }

  const TABLE_HEADS = [
    "Type", "Vendor", "Model", "IP Address", "Port",
    "Site ID", "Serial", "Firmware", "MAC", "Username", "Status", "Actions",
  ];

  return (
    <div className="flex-1 flex flex-col bg-background min-h-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <Server size={16} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Devices</span>
          <span className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
            {devices.length}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 bg-muted border border-border rounded px-2.5 py-1.5 w-52">
            <Search size={12} className="text-muted-foreground flex-shrink-0" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search devices…"
              className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full"
            />
          </div>
          <button
            onClick={loadDevices}
            title="Refresh"
            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
          >
            <RefreshCw size={14} />
          </button>
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary/90 text-white text-xs font-medium rounded transition-colors"
          >
            <Plus size={14} />
            Add Device
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading && (
          <div className="flex items-center justify-center h-40 text-xs text-muted-foreground">
            Loading…
          </div>
        )}

        {!loading && error && (
          <div className="flex items-center justify-center h-40 text-xs text-red-400">
            {error}
          </div>
        )}

        {!loading && !error && (
          <Table>
            <TableHeader>
              <TableRow className="border-border">
                {TABLE_HEADS.map((h) => (
                  <TableHead
                    key={h}
                    className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide py-2.5 px-3 bg-card"
                  >
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={TABLE_HEADS.length}
                    className="text-center text-xs text-muted-foreground py-12"
                  >
                    {search
                      ? "No devices match your search."
                      : 'No devices yet. Click "Add Device" to create one.'}
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((d) => (
                  <TableRow key={d.id} className="border-border hover:bg-secondary/20">
                    <TableCell className="px-3 py-2">
                      <span className="text-xs font-medium text-foreground">{d.device_type}</span>
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs text-foreground">
                      {d.vendor || <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs text-foreground">
                      {d.model || <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs font-mono text-foreground">
                      {d.ip_address || <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs text-foreground">
                      {d.port ?? <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs font-mono text-muted-foreground max-w-[110px] truncate">
                      {d.site_id ? (
                        <span title={d.site_id}>{d.site_id.slice(0, 8)}…</span>
                      ) : (
                        <span>—</span>
                      )}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs text-muted-foreground">
                      {d.serial_number || "—"}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs text-muted-foreground">
                      {d.firmware_version || "—"}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs font-mono text-muted-foreground">
                      {d.mac_address || "—"}
                    </TableCell>
                    <TableCell className="px-3 py-2 text-xs text-muted-foreground">
                      {d.username || "—"}
                    </TableCell>
                    <TableCell className="px-3 py-2">
                      <StatusBadge status={d.status} />
                    </TableCell>
                    <TableCell className="px-3 py-2">
                      {deleteConfirm === d.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleDelete(d.id)}
                            className="text-[11px] px-2 py-0.5 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(null)}
                            className="p-0.5 rounded text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => openEdit(d)}
                            title="Edit"
                            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <Pencil size={13} />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(d.id)}
                            title="Delete"
                            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </div>

      <DeviceDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        editTarget={editTarget}
        onSaved={loadDevices}
      />
    </div>
  );
}
