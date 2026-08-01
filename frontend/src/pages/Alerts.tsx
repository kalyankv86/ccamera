import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { pollingInterval } from "../api/ws";
import { useAuth } from "../state/auth";
import { useWsStatus } from "../state/wsStatus";
import { SeverityBadge } from "../components/StateBadge";
import type { Alert, AlertStateT } from "../api/types";

export function Alerts() {
  const connected = useWsStatus((s) => s.connected);
  const user = useAuth((s) => s.user);
  const queryClient = useQueryClient();
  const [stateFilter, setStateFilter] = useState<AlertStateT | "">("open");

  const { data: alerts } = useQuery({
    queryKey: ["alerts", stateFilter],
    queryFn: () => api.get<Alert[]>(`/alerts${stateFilter ? `?state=${stateFilter}` : ""}`),
    refetchInterval: pollingInterval(connected),
  });

  const ackMutation = useMutation({
    mutationFn: (alertId: number) => api.post(`/alerts/${alertId}/ack`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const canAck = user?.role === "admin" || user?.role === "security_officer" || user?.role === "technician";

  return (
    <div>
      <div className="page-header">
        <h2>Alerts</h2>
      </div>

      <div className="filters">
        <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value as AlertStateT | "")}>
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="acked">Acknowledged</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      <table>
        <thead>
          <tr>
            <th>Device</th>
            <th>Type</th>
            <th>Severity</th>
            <th>State</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(alerts ?? []).map((a) => (
            <tr key={a.id}>
              <td><Link to={`/devices/${a.device_id}`}>{a.device_name}</Link></td>
              <td>{a.type}</td>
              <td><SeverityBadge severity={a.severity} /></td>
              <td>{a.state}</td>
              <td>{new Date(a.created_at).toLocaleString()}</td>
              <td>
                {a.state === "open" && canAck && (
                  <button
                    className="ack-btn"
                    disabled={ackMutation.isPending}
                    onClick={() => ackMutation.mutate(a.id)}
                  >
                    Acknowledge
                  </button>
                )}
                {a.state === "acked" && <span style={{ fontSize: 12, color: "var(--text-muted)" }}>acked</span>}
              </td>
            </tr>
          ))}
          {(alerts ?? []).length === 0 && (
            <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>No alerts.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
