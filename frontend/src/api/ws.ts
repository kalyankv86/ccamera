import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../state/auth";
import { useWsStatus } from "../state/wsStatus";
import type { StatusChangeMessage } from "./types";

/** SDD 3.7: WebSocket push with a 15s-polling fallback. Connects to
 * /api/v1/status/live, invalidates the relevant queries on each push so
 * TanStack Query refetches, and reports its own connection status so pages
 * can drop their refetchInterval to 15s only while genuinely disconnected. */
export function useStatusLiveSocket() {
  const token = useAuth((s) => s.token);
  const queryClient = useQueryClient();
  const [connected, setConnectedLocal] = useState(false);
  const setConnectedShared = useWsStatus((s) => s.setConnected);
  const setConnected = (value: boolean) => {
    setConnectedLocal(value);
    setConnectedShared(value);
  };
  const retryRef = useRef(0);

  useEffect(() => {
    if (!token) return;
    let ws: WebSocket | null = null;
    let closedByEffect = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${proto}//${location.host}/api/v1/status/live?token=${token}`);

      ws.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
      };
      ws.onmessage = (event) => {
        const msg: StatusChangeMessage = JSON.parse(event.data);
        queryClient.invalidateQueries({ queryKey: ["status-summary"] });
        queryClient.invalidateQueries({ queryKey: ["devices"] });
        queryClient.invalidateQueries({ queryKey: ["device", msg.device_id] });
        queryClient.invalidateQueries({ queryKey: ["alerts"] });
      };
      ws.onclose = () => {
        setConnected(false);
        if (closedByEffect) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
        retryRef.current += 1;
        retryTimer = setTimeout(connect, delay);
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closedByEffect = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
    };
  }, [token, queryClient]);

  return { connected };
}

/** While the socket is down, pages poll every 15s instead. */
export function pollingInterval(connected: boolean): number | false {
  return connected ? false : 15000;
}
