import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { pollingInterval } from "../api/ws";
import { useAuth } from "../state/auth";
import { useWsStatus } from "../state/wsStatus";
import { StateBadge } from "../components/StateBadge";
import type { Device } from "../api/types";

export function DevicesList() {
  const connected = useWsStatus((s) => s.connected);
  const user = useAuth((s) => s.user);
  const { data: devices } = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.get<Device[]>("/devices"),
    refetchInterval: pollingInterval(connected),
  });

  const [building, setBuilding] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [criticalityFilter, setCriticalityFilter] = useState("");

  const buildings = useMemo(
    () => Array.from(new Set((devices ?? []).map((d) => d.building).filter(Boolean))) as string[],
    [devices],
  );

  const filtered = (devices ?? []).filter((d) => {
    if (building && d.building !== building) return false;
    if (stateFilter && d.current_state !== stateFilter) return false;
    if (criticalityFilter && d.criticality !== criticalityFilter) return false;
    return true;
  });

  return (
    <div>
      <div className="page-header">
        <h2>Devices</h2>
        {user?.role === "admin" && (
          <Link to="/devices/new" className="ack-btn">+ Add device</Link>
        )}
      </div>

      <div className="filters">
        <select value={building} onChange={(e) => setBuilding(e.target.value)}>
          <option value="">All buildings</option>
          {buildings.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
        <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
          <option value="">All states</option>
          {["UP", "DEGRADED", "DOWN", "MAINTENANCE", "UNKNOWN"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select value={criticalityFilter} onChange={(e) => setCriticalityFilter(e.target.value)}>
          <option value="">All criticality</option>
          {["critical", "high", "normal"].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>IP</th>
            <th>Building / Zone</th>
            <th>Criticality</th>
            <th>State</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((d) => (
            <tr key={d.id}>
              <td><Link to={`/devices/${d.id}`}>{d.name}</Link></td>
              <td>{d.type}</td>
              <td>{d.ip}</td>
              <td>{d.building} / {d.zone}</td>
              <td>{d.criticality}</td>
              <td><StateBadge state={d.current_state} /></td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>No devices match these filters.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
