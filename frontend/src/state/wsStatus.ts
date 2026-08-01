import { create } from "zustand";

interface WsStatusState {
  connected: boolean;
  setConnected: (connected: boolean) => void;
}

/** Shared between Layout (owns the actual socket) and any page that needs to
 * know whether to fall back to 15s polling (SDD 3.7). */
export const useWsStatus = create<WsStatusState>((set) => ({
  connected: false,
  setConnected: (connected) => set({ connected }),
}));
