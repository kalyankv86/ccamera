import { create } from "zustand";

export interface CurrentUser {
  id: number;
  name: string;
  email: string;
  role: "admin" | "security_officer" | "technician" | "viewer";
  vendor_id: number | null;
}

interface AuthState {
  token: string | null;
  user: CurrentUser | null;
  setSession: (token: string, user: CurrentUser) => void;
  logout: () => void;
}

const STORAGE_KEY = "ccms_token";

export const useAuth = create<AuthState>((set) => ({
  token: localStorage.getItem(STORAGE_KEY),
  user: null,
  setSession: (token, user) => {
    localStorage.setItem(STORAGE_KEY, token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({ token: null, user: null });
  },
}));
