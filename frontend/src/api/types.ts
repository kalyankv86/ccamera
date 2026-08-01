export type DeviceState = "UP" | "DEGRADED" | "DOWN" | "MAINTENANCE" | "UNKNOWN";
export type DeviceType = "camera" | "nvr" | "switch";
export type Criticality = "critical" | "high" | "normal";
export type AlertSeverity = "critical" | "warning" | "info";
export type AlertStateT = "open" | "acked" | "closed";

export interface Device {
  id: number;
  type: DeviceType;
  name: string;
  make: string | null;
  model: string | null;
  ip: string;
  rtsp_url: string | null;
  onvif_url: string | null;
  parent_nvr_id: number | null;
  channel_no: number | null;
  building: string | null;
  zone: string | null;
  lat: number | null;
  lng: number | null;
  vendor_id: number | null;
  criticality: Criticality;
  active: boolean;
  current_state: DeviceState;
  ping_interval_s: number;
  rtsp_interval_s: number;
  created_at: string;
  updated_at: string;
}

export interface StatusCounts {
  total: number;
  up: number;
  degraded: number;
  down: number;
  maintenance: number;
  unknown: number;
}

export interface StatusSummary {
  overall: StatusCounts;
  by_building: { key: string; counts: StatusCounts }[];
}

export interface Alert {
  id: number;
  device_id: number;
  device_name: string;
  group_id: string | null;
  type: string;
  severity: AlertSeverity;
  state: AlertStateT;
  created_at: string;
  acked_by: number | null;
  acked_at: string | null;
  closed_at: string | null;
}

export interface DeviceHistoryEvent {
  old_state: DeviceState;
  new_state: DeviceState;
  cause: string | null;
  started_at: string;
  ended_at: string | null;
  downtime_seconds: number | null;
  suppressed_by_parent: boolean;
}

export interface DeviceCheckResult {
  time: string;
  check_type: string;
  status: string;
  latency_ms: number | null;
  loss_pct: number | null;
}

export interface DeviceHistory {
  status_events: DeviceHistoryEvent[];
  recent_checks: DeviceCheckResult[];
  uptime_pct_24h: number | null;
}

export interface StatusChangeMessage {
  device_id: number;
  old_state: DeviceState;
  new_state: DeviceState;
}
