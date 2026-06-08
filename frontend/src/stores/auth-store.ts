"use client";

import { create } from "zustand";
import {
  getMe,
  login as loginRequest,
  logout as logoutRequest,
  type UserIdentity,
} from "@/lib/api/auth";

type AuthStatus = "idle" | "checking" | "authenticated" | "anonymous";

interface AuthState {
  user: UserIdentity | null;
  status: AuthStatus;
  error: string | null;
  refresh: () => Promise<UserIdentity | null>;
  login: (email: string) => Promise<UserIdentity | null>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  status: "idle",
  error: null,
  refresh: async () => {
    set({ status: "checking", error: null });
    try {
      const user = await getMe();
      set({ user, status: "authenticated" });
      return user;
    } catch {
      set({ user: null, status: "anonymous" });
      return null;
    }
  },
  login: async (email) => {
    set({ status: "checking", error: null });
    try {
      await loginRequest(email);
      return get().refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "登录失败";
      set({ user: null, status: "anonymous", error: message });
      throw error;
    }
  },
  logout: async () => {
    try {
      await logoutRequest();
    } finally {
      set({ user: null, status: "anonymous", error: null });
    }
  },
  clearError: () => set({ error: null }),
}));
