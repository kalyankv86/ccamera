import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import type { AdminUser, MaintenanceWindow, MaintenanceScope, UserRole } from "../api/adminTypes";

function MaintenanceTab() {
  const queryClient = useQueryClient();
  const { data: windows } = useQuery({
    queryKey: ["maintenance-windows"],
    queryFn: () => api.get<MaintenanceWindow[]>("/admin/maintenance"),
  });

  const [scopeType, setScopeType] = useState<MaintenanceScope>("campus");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      api.post("/admin/maintenance", {
        scope_type: scopeType,
        starts_at: new Date(startsAt).toISOString(),
        ends_at: new Date(endsAt).toISOString(),
        reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] });
      setStartsAt("");
      setEndsAt("");
      setReason("");
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Failed to create window"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.del(`/admin/maintenance/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] }),
  });

  return (
    <div>
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>New maintenance window</h3>
        {error && <div className="error-text">{error}</div>}
        <div className="filters" style={{ flexWrap: "wrap" }}>
          <select value={scopeType} onChange={(e) => setScopeType(e.target.value as MaintenanceScope)}>
            <option value="campus">Whole campus</option>
            <option value="building">Building</option>
            <option value="group">NVR group</option>
            <option value="device">Single device</option>
          </select>
          <input type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required />
          <input type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} required />
          <input type="text" placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          <button
            className="ack-btn"
            disabled={!startsAt || !endsAt || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            Create
          </button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Active / scheduled windows</h3>
        <table>
          <thead>
            <tr>
              <th>Scope</th>
              <th>Starts</th>
              <th>Ends</th>
              <th>Reason</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(windows ?? []).map((w) => (
              <tr key={w.id}>
                <td>{w.scope_type}</td>
                <td>{new Date(w.starts_at).toLocaleString()}</td>
                <td>{new Date(w.ends_at).toLocaleString()}</td>
                <td>{w.reason ?? "-"}</td>
                <td>
                  <button className="ack-btn" onClick={() => deleteMutation.mutate(w.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {(windows ?? []).length === 0 && (
              <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)" }}>No maintenance windows.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UsersTab() {
  const queryClient = useQueryClient();
  const { data: users } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api.get<AdminUser[]>("/admin/users"),
  });

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("viewer");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => api.post("/admin/users", { name, email, password, role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setName("");
      setEmail("");
      setPassword("");
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Failed to create user"),
  });

  return (
    <div>
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>New user</h3>
        {error && <div className="error-text">{error}</div>}
        <div className="filters" style={{ flexWrap: "wrap" }}>
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
            <option value="admin">Administrator</option>
            <option value="security_officer">Security Officer</option>
            <option value="technician">Technician</option>
            <option value="viewer">Viewer</option>
          </select>
          <button
            className="ack-btn"
            disabled={!name || !email || !password || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            Create
          </button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Users</h3>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {(users ?? []).map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>{u.active ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Admin() {
  const [tab, setTab] = useState<"maintenance" | "users">("maintenance");

  return (
    <div>
      <div className="page-header">
        <h2>Admin</h2>
      </div>
      <div className="filters">
        <button className="ack-btn" style={{ fontWeight: tab === "maintenance" ? 700 : 400 }} onClick={() => setTab("maintenance")}>
          Maintenance windows
        </button>
        <button className="ack-btn" style={{ fontWeight: tab === "users" ? 700 : 400 }} onClick={() => setTab("users")}>
          Users
        </button>
      </div>
      {tab === "maintenance" ? <MaintenanceTab /> : <UsersTab />}
    </div>
  );
}
