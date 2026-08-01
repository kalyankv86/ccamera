import { useQuery } from "@tanstack/react-query";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { pollingInterval } from "../api/ws";
import { useWsStatus } from "../state/wsStatus";
import type { Device, StatusSummary } from "../api/types";

const STATE_COLOR: Record<string, string> = {
  UP: "#1a9c4a",
  DEGRADED: "#d98c00",
  DOWN: "#d13438",
  MAINTENANCE: "#8a8a8a",
  UNKNOWN: "#b0b0b0",
};

export function Summary() {
  const connected = useWsStatus((s) => s.connected);
  const { data: summary } = useQuery({
    queryKey: ["status-summary"],
    queryFn: () => api.get<StatusSummary>("/status/summary"),
    refetchInterval: pollingInterval(connected),
  });
  const { data: devices } = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.get<Device[]>("/devices"),
    refetchInterval: pollingInterval(connected),
  });

  const overall = summary?.overall;
  const mappable = (devices ?? []).filter((d) => d.lat != null && d.lng != null);
  const center: [number, number] =
    mappable.length > 0 ? [mappable[0].lat as number, mappable[0].lng as number] : [20.2961, 85.8245];

  return (
    <div>
      <div className="page-header">
        <h2>Summary</h2>
      </div>

      <div className="stat-row">
        <div className="stat-tile">
          <div className="value">{overall?.total ?? "-"}</div>
          <div className="label">Total</div>
        </div>
        <div className="stat-tile" style={{ borderColor: STATE_COLOR.UP }}>
          <div className="value" style={{ color: STATE_COLOR.UP }}>{overall?.up ?? "-"}</div>
          <div className="label">Up</div>
        </div>
        <div className="stat-tile" style={{ borderColor: STATE_COLOR.DEGRADED }}>
          <div className="value" style={{ color: STATE_COLOR.DEGRADED }}>{overall?.degraded ?? "-"}</div>
          <div className="label">Degraded</div>
        </div>
        <div className="stat-tile" style={{ borderColor: STATE_COLOR.DOWN }}>
          <div className="value" style={{ color: STATE_COLOR.DOWN }}>{overall?.down ?? "-"}</div>
          <div className="label">Down</div>
        </div>
        <div className="stat-tile">
          <div className="value" style={{ color: STATE_COLOR.MAINTENANCE }}>{overall?.maintenance ?? "-"}</div>
          <div className="label">Maintenance</div>
        </div>
      </div>

      <div className="card" style={{ padding: 0, marginBottom: 24 }}>
        <div className="map-container">
          <MapContainer center={center} zoom={17} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />
            {mappable.map((d) => (
              <CircleMarker
                key={d.id}
                center={[d.lat as number, d.lng as number]}
                radius={9}
                pathOptions={{ color: STATE_COLOR[d.current_state], fillColor: STATE_COLOR[d.current_state], fillOpacity: 0.9 }}
              >
                <Popup>
                  <strong>{d.name}</strong>
                  <br />
                  {d.building} - {d.zone}
                  <br />
                  State: {d.current_state}
                  <br />
                  <Link to={`/devices/${d.id}`}>View detail</Link>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </div>

      {summary && summary.by_building.length > 0 && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>By building</h3>
          <table>
            <thead>
              <tr>
                <th>Building</th>
                <th>Total</th>
                <th>Up</th>
                <th>Degraded</th>
                <th>Down</th>
                <th>Maintenance</th>
              </tr>
            </thead>
            <tbody>
              {summary.by_building.map((row) => (
                <tr key={row.key}>
                  <td>{row.key}</td>
                  <td>{row.counts.total}</td>
                  <td>{row.counts.up}</td>
                  <td>{row.counts.degraded}</td>
                  <td>{row.counts.down}</td>
                  <td>{row.counts.maintenance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
