import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { pollingInterval } from "../api/ws";
import { useAuth } from "../state/auth";
import { useWsStatus } from "../state/wsStatus";
import { StateBadge } from "../components/StateBadge";
import type { Device, DeviceHistory } from "../api/types";

export function DeviceDetail() {
  const { id } = useParams();
  const deviceId = Number(id);
  const connected = useWsStatus((s) => s.connected);
  const token = useAuth((s) => s.token);

  const { data: device } = useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => api.get<Device>(`/devices/${deviceId}`),
    refetchInterval: pollingInterval(connected),
  });
  const { data: history } = useQuery({
    queryKey: ["device-history", deviceId],
    queryFn: () => api.get<DeviceHistory>(`/devices/${deviceId}/history`),
    refetchInterval: pollingInterval(connected),
  });

  if (!device) return <p>Loading...</p>;

  const latencyPoints = (history?.recent_checks ?? [])
    .filter((c) => c.check_type === "PING" && c.latency_ms != null)
    .slice()
    .reverse()
    .map((c) => ({ time: new Date(c.time).toLocaleTimeString(), latency_ms: c.latency_ms }));

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/devices">&larr; Devices</Link>
          <h2 style={{ margin: "4px 0 0" }}>{device.name}</h2>
        </div>
        <StateBadge state={device.current_state} />
      </div>

      <div className="stat-row">
        <div className="stat-tile">
          <div className="value">{history?.uptime_pct_24h ?? "-"}%</div>
          <div className="label">Uptime (24h)</div>
        </div>
        <div className="stat-tile">
          <div className="value" style={{ fontSize: 16 }}>{device.ip}</div>
          <div className="label">IP address</div>
        </div>
        <div className="stat-tile">
          <div className="value" style={{ fontSize: 16 }}>{device.building} / {device.zone}</div>
          <div className="label">Location</div>
        </div>
        <div className="stat-tile">
          <div className="value" style={{ fontSize: 16 }}>{device.criticality}</div>
          <div className="label">Criticality</div>
        </div>
      </div>

      {device.type === "camera" && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Latest snapshot</h3>
          <img
            src={`/api/v1/devices/${deviceId}/snapshot?token=${token}`}
            alt="Latest snapshot"
            style={{ maxWidth: 320, borderRadius: 4, border: "1px solid var(--border)" }}
            onError={(e) => ((e.target as HTMLImageElement).style.display = "none")}
          />
        </div>
      )}

      {latencyPoints.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Ping latency</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={latencyPoints}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit="ms" />
              <Tooltip />
              <Line type="monotone" dataKey="latency_ms" stroke="var(--accent, #2f6fed)" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginTop: 0 }}>Downtime log</h3>
        <table>
          <thead>
            <tr>
              <th>Transition</th>
              <th>Cause</th>
              <th>Started</th>
              <th>Downtime</th>
            </tr>
          </thead>
          <tbody>
            {(history?.status_events ?? []).map((e, i) => (
              <tr key={i}>
                <td>{e.old_state} &rarr; {e.new_state}{e.suppressed_by_parent ? " (suppressed)" : ""}</td>
                <td>{e.cause ?? "-"}</td>
                <td>{new Date(e.started_at).toLocaleString()}</td>
                <td>{e.downtime_seconds != null ? `${Math.floor(e.downtime_seconds / 60)}m ${e.downtime_seconds % 60}s` : "-"}</td>
              </tr>
            ))}
            {(history?.status_events ?? []).length === 0 && (
              <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--text-muted)" }}>No state changes recorded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Recent checks</h3>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Type</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Loss</th>
            </tr>
          </thead>
          <tbody>
            {(history?.recent_checks ?? []).slice(0, 30).map((c, i) => (
              <tr key={i}>
                <td>{new Date(c.time).toLocaleTimeString()}</td>
                <td>{c.check_type}</td>
                <td>{c.status}</td>
                <td>{c.latency_ms != null ? `${c.latency_ms} ms` : "-"}</td>
                <td>{c.loss_pct != null ? `${c.loss_pct}%` : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
