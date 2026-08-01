import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useAuth } from "../state/auth";

interface DeviceUptimeRow {
  device_id: number;
  device_name: string;
  building: string | null;
  vendor_name: string | null;
  uptime_pct: number;
  downtime_seconds: number;
  sla_target_pct: number | null;
  sla_met: boolean | null;
}

interface UptimeReport {
  devices: DeviceUptimeRow[];
  by_building: Record<string, number>;
}

function isoDate(d: Date) {
  return d.toISOString().slice(0, 10);
}

export function Reports() {
  const token = useAuth((s) => s.token);
  const [from, setFrom] = useState(isoDate(new Date(Date.now() - 30 * 86400 * 1000)));
  const [to, setTo] = useState(isoDate(new Date()));

  const { data } = useQuery({
    queryKey: ["uptime-report", from, to],
    queryFn: () => api.get<UptimeReport>(`/reports/uptime?from=${from}T00:00:00Z&to=${to}T23:59:59Z&format=json`),
  });

  const downloadUrl = (format: "pdf" | "xlsx") =>
    `/api/v1/reports/uptime?from=${from}T00:00:00Z&to=${to}T23:59:59Z&format=${format}&token=${token}`;

  return (
    <div>
      <div className="page-header">
        <h2>Reports</h2>
      </div>

      <div className="filters">
        <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        <a className="ack-btn" href={downloadUrl("pdf")} target="_blank" rel="noreferrer">Download PDF</a>
        <a className="ack-btn" href={downloadUrl("xlsx")} target="_blank" rel="noreferrer">Download Excel</a>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Device</th>
              <th>Building</th>
              <th>Vendor</th>
              <th>Uptime %</th>
              <th>Downtime</th>
              <th>SLA Target</th>
              <th>Met?</th>
            </tr>
          </thead>
          <tbody>
            {(data?.devices ?? []).map((r) => (
              <tr key={r.device_id}>
                <td>{r.device_name}</td>
                <td>{r.building ?? "-"}</td>
                <td>{r.vendor_name ?? "-"}</td>
                <td>{r.uptime_pct.toFixed(2)}%</td>
                <td>{Math.floor(r.downtime_seconds / 60)}m</td>
                <td>{r.sla_target_pct != null ? `${r.sla_target_pct}%` : "-"}</td>
                <td>{r.sla_met == null ? "-" : r.sla_met ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
