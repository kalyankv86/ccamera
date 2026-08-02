import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Device } from "../api/types";

interface DeviceFormState {
  type: "camera" | "nvr" | "switch";
  name: string;
  ip: string;
  make: string;
  model: string;
  building: string;
  zone: string;
  criticality: "critical" | "high" | "normal";
  rtsp_url: string;
  onvif_url: string;
  credential_username: string;
  credential_password: string;
}

const EMPTY: DeviceFormState = {
  type: "nvr",
  name: "",
  ip: "",
  make: "",
  model: "",
  building: "",
  zone: "",
  criticality: "normal",
  rtsp_url: "",
  onvif_url: "",
  credential_username: "",
  credential_password: "",
};

export function AddDevice() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<DeviceFormState>(EMPTY);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof DeviceFormState>(key: K, value: DeviceFormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const createMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        type: form.type,
        name: form.name,
        ip: form.ip,
        criticality: form.criticality,
      };
      if (form.make) payload.make = form.make;
      if (form.model) payload.model = form.model;
      if (form.building) payload.building = form.building;
      if (form.zone) payload.zone = form.zone;
      if (form.rtsp_url) payload.rtsp_url = form.rtsp_url;
      if (form.onvif_url) payload.onvif_url = form.onvif_url;
      if (form.credential_username) payload.credential_username = form.credential_username;
      if (form.credential_password) payload.credential_password = form.credential_password;
      return api.post<Device>("/devices", payload);
    },
    onSuccess: (device) => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      navigate(`/devices/${device.id}`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Failed to create device"),
  });

  const csvMutation = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api.post<Device[]>("/devices/import", body);
    },
    onSuccess: (devices) => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      navigate("/devices");
      alert(`Imported ${devices.length} device(s).`);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "CSV import failed"),
  });

  return (
    <div>
      <div className="page-header">
        <h2>Add device</h2>
      </div>

      {error && <div className="error-text">{error}</div>}

      <div className="card" style={{ marginBottom: 24, maxWidth: 640 }}>
        <h3 style={{ marginTop: 0 }}>Single device</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
        >
          <div className="filters" style={{ flexWrap: "wrap" }}>
            <select value={form.type} onChange={(e) => set("type", e.target.value as DeviceFormState["type"])}>
              <option value="nvr">NVR</option>
              <option value="camera">Camera</option>
              <option value="switch">Switch</option>
            </select>
            <select value={form.criticality} onChange={(e) => set("criticality", e.target.value as DeviceFormState["criticality"])}>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="filters" style={{ flexWrap: "wrap" }}>
            <input placeholder="Name *" value={form.name} onChange={(e) => set("name", e.target.value)} required style={{ flex: 1 }} />
            <input placeholder="IP address *" value={form.ip} onChange={(e) => set("ip", e.target.value)} required />
          </div>
          <div className="filters" style={{ flexWrap: "wrap" }}>
            <input placeholder="Make" value={form.make} onChange={(e) => set("make", e.target.value)} />
            <input placeholder="Model" value={form.model} onChange={(e) => set("model", e.target.value)} />
          </div>
          <div className="filters" style={{ flexWrap: "wrap" }}>
            <input placeholder="Building" value={form.building} onChange={(e) => set("building", e.target.value)} />
            <input placeholder="Zone" value={form.zone} onChange={(e) => set("zone", e.target.value)} />
          </div>
          {form.type === "camera" && (
            <div className="filters" style={{ flexWrap: "wrap" }}>
              <input
                placeholder="RTSP URL (rtsp://ip:554/...)"
                value={form.rtsp_url}
                onChange={(e) => set("rtsp_url", e.target.value)}
                style={{ flex: 1 }}
              />
            </div>
          )}
          {form.type === "nvr" && (
            <div className="filters" style={{ flexWrap: "wrap" }}>
              <input
                placeholder="ONVIF/vendor API URL (optional)"
                value={form.onvif_url}
                onChange={(e) => set("onvif_url", e.target.value)}
                style={{ flex: 1 }}
              />
            </div>
          )}
          <div className="filters" style={{ flexWrap: "wrap" }}>
            <input placeholder="Credential username" value={form.credential_username} onChange={(e) => set("credential_username", e.target.value)} />
            <input
              placeholder="Credential password"
              type="password"
              value={form.credential_password}
              onChange={(e) => set("credential_password", e.target.value)}
            />
          </div>
          <button className="ack-btn" type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create device"}
          </button>
        </form>
      </div>

      <div className="card" style={{ maxWidth: 640 }}>
        <h3 style={{ marginTop: 0 }}>Bulk import (CSV)</h3>
        <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
          Columns match the single-device fields above: type, name, ip, make, model, building, zone,
          criticality, rtsp_url, onvif_url, credential_username, credential_password. Leave a cell blank to
          omit that field.
        </p>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) csvMutation.mutate(file);
          }}
          disabled={csvMutation.isPending}
        />
      </div>
    </div>
  );
}
