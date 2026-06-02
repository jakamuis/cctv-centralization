import { useState, useEffect, useCallback } from "react";
import { Users, Plus, Pencil, Trash2, X, RefreshCw, Search, ShieldCheck } from "lucide-react";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter,
} from "../components/ui/sheet";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import { usersApi } from "../api";

const inputCls  = "w-full bg-muted border border-border rounded px-2.5 py-1.5 text-xs text-foreground placeholder-muted-foreground outline-none focus:border-primary/50 transition-colors";

const EMPTY_FORM = { username: "", full_name: "", email: "", password: "", is_active: true };

function fmt(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" });
}

function RoleBadge({ name }) {
  const map = {
    SUPER_ADMIN: "bg-red-500/15 text-red-400",
    OPERATOR:    "bg-blue-500/15 text-blue-400",
    VIEWER:      "bg-secondary text-muted-foreground",
  };
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${map[name] || "bg-secondary text-muted-foreground"}`}>
      {name}
    </span>
  );
}

function UserDrawer({ open, onOpenChange, editTarget, onSaved }) {
  const [form,      setForm]      = useState(EMPTY_FORM);
  const [saving,    setSaving]    = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setSaveError(null);
    setForm(editTarget
      ? { username: editTarget.username || "", full_name: editTarget.full_name || "", email: editTarget.email || "", password: "", is_active: editTarget.is_active ?? true }
      : EMPTY_FORM
    );
  }, [open, editTarget]);

  function set(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSave() {
    setSaving(true); setSaveError(null);
    try {
      const payload = { username: form.username, full_name: form.full_name || null, email: form.email, is_active: form.is_active };
      if (form.password) payload.password = form.password;
      if (editTarget) await usersApi.update(editTarget.id, payload);
      else            await usersApi.create({ ...payload, password: form.password });
      onOpenChange(false);
      onSaved();
    } catch (e) {
      setSaveError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[400px] sm:max-w-[400px] bg-card border-l border-border flex flex-col p-0 gap-0">
        <SheetHeader className="px-5 py-4 border-b border-border">
          <SheetTitle className="text-sm font-semibold">{editTarget ? "Edit User" : "Add User"}</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3.5">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Username <span className="text-red-400">*</span></label>
            <input value={form.username} onChange={e => set("username", e.target.value)} placeholder="johndoe" className={inputCls} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Full Name</label>
            <input value={form.full_name} onChange={e => set("full_name", e.target.value)} placeholder="John Doe" className={inputCls} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Email <span className="text-red-400">*</span></label>
            <input type="email" value={form.email} onChange={e => set("email", e.target.value)} placeholder="john@example.com" className={inputCls} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">{editTarget ? "Password (blank = unchanged)" : "Password *"}</label>
            <input type="password" value={form.password} onChange={e => set("password", e.target.value)} placeholder="••••••••" className={inputCls} />
          </div>
          <div className="flex items-center gap-2.5">
            <input type="checkbox" id="is_active" checked={form.is_active} onChange={e => set("is_active", e.target.checked)} className="w-3.5 h-3.5 accent-primary" />
            <label htmlFor="is_active" className="text-xs text-foreground cursor-pointer">Active</label>
          </div>
          {saveError && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2 leading-relaxed">{saveError}</p>
          )}
        </div>

        <SheetFooter className="flex flex-row gap-2 px-5 py-4 border-t border-border">
          <button onClick={() => onOpenChange(false)} className="flex-1 px-3 py-2 rounded border border-border text-xs text-foreground hover:bg-secondary transition-colors">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="flex-1 px-3 py-2 rounded bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-xs font-medium transition-colors">
            {saving ? "Saving…" : editTarget ? "Save Changes" : "Add User"}
          </button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

export default function UsersPage() {
  const [users,         setUsers]         = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState(null);
  const [search,        setSearch]        = useState("");
  const [drawerOpen,    setDrawerOpen]    = useState(false);
  const [editTarget,    setEditTarget]    = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    usersApi.list()
      .then(d => setUsers(Array.isArray(d) ? d : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = users.filter(u =>
    search === "" ||
    [u.username, u.full_name, u.email]
      .filter(Boolean)
      .some(v => v.toLowerCase().includes(search.toLowerCase()))
  );

  async function handleDelete(id) {
    try { await usersApi.remove(id); } catch {}
    finally { setDeleteConfirm(null); load(); }
  }

  const HEADS = ["Username", "Full Name", "Email", "Roles", "Status", "Created", "Actions"];

  return (
    <div className="flex-1 flex flex-col bg-background min-h-0 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <Users size={16} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Users</span>
          <span className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">{users.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 bg-muted border border-border rounded px-2.5 py-1.5 w-52">
            <Search size={12} className="text-muted-foreground flex-shrink-0" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search users…" className="bg-transparent text-xs text-foreground placeholder-muted-foreground outline-none w-full" />
          </div>
          <button onClick={load} className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"><RefreshCw size={14} /></button>
          <button onClick={() => { setEditTarget(null); setDrawerOpen(true); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary/90 text-white text-xs font-medium rounded transition-colors">
            <Plus size={14} /> Add User
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {loading && <div className="flex items-center justify-center h-40 text-xs text-muted-foreground">Loading…</div>}
        {!loading && error && <div className="flex items-center justify-center h-40 text-xs text-red-400">{error}</div>}
        {!loading && !error && (
          <Table>
            <TableHeader>
              <TableRow className="border-border">
                {HEADS.map(h => <TableHead key={h} className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide py-2.5 px-3 bg-card">{h}</TableHead>)}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow><TableCell colSpan={HEADS.length} className="text-center text-xs text-muted-foreground py-12">{search ? "No matches." : "No users found."}</TableCell></TableRow>
              ) : filtered.map(u => (
                <TableRow key={u.id} className="border-border hover:bg-secondary/20">
                  <TableCell className="px-3 py-2 text-xs font-medium text-foreground">{u.username}</TableCell>
                  <TableCell className="px-3 py-2 text-xs text-foreground">{u.full_name || <span className="text-muted-foreground">—</span>}</TableCell>
                  <TableCell className="px-3 py-2 text-xs text-muted-foreground">{u.email}</TableCell>
                  <TableCell className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(u.roles || []).map(r => <RoleBadge key={r.id || r.name} name={r.name} />)}
                      {!(u.roles || []).length && <span className="text-[11px] text-muted-foreground">—</span>}
                    </div>
                  </TableCell>
                  <TableCell className="px-3 py-2">
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${u.is_active ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </TableCell>
                  <TableCell className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">{fmt(u.created_at)}</TableCell>
                  <TableCell className="px-3 py-2">
                    {deleteConfirm === u.id ? (
                      <div className="flex items-center gap-1">
                        <button onClick={() => handleDelete(u.id)} className="text-[11px] px-2 py-0.5 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors">Confirm</button>
                        <button onClick={() => setDeleteConfirm(null)} className="p-0.5 rounded text-muted-foreground hover:text-foreground"><X size={12} /></button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1">
                        <button onClick={() => { setEditTarget(u); setDrawerOpen(true); }} className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"><Pencil size={13} /></button>
                        <button onClick={() => setDeleteConfirm(u.id)} className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-red-400 transition-colors"><Trash2 size={13} /></button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <UserDrawer open={drawerOpen} onOpenChange={setDrawerOpen} editTarget={editTarget} onSaved={load} />
    </div>
  );
}
