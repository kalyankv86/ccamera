import type { AlertSeverity, DeviceState } from "../api/types";

export function StateBadge({ state }: { state: DeviceState }) {
  return <span className={`badge state-${state}`}>{state}</span>;
}

export function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  return <span className={`badge severity-${severity}`}>{severity}</span>;
}
