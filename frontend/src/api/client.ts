import { useAuth } from "../state/auth";

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuth.getState().token;
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (init?.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    useAuth.getState().logout();
    throw new ApiError(401, "Session expired");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore parse failure */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function serialize(body: unknown): BodyInit | undefined {
  if (body === undefined) return undefined;
  if (body instanceof FormData) return body;
  return JSON.stringify(body);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: serialize(body) }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: serialize(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
