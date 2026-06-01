"use client";

import { create } from "zustand";
import {
  getMe,
  logout as logoutRequest,
  sendCode,
  type UserIdentity,
  verifyCode,
} from "@/lib/api/auth";

type AuthStatus = "idle" | "checking" | "authenticated" | "anonymous";

interface AuthState {
  user: UserIdentity | null;
  status: AuthStatus;
  devCode: string | null;
  error: string | null;
  refresh: () => Promise<UserIdentity | null>;
  requestCode: (email: string) => Promise<void>;
  verify: (email: string, code: string) => Promise<UserIdentity | null>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  status: "idle",
  devCode: null,
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
  requestCode: async (email) => {
    set({ error: null, devCode: null });
    try {
      const response = await sendCode(email);
      set({ devCode: response.dev_code });
    } catch (error) {
      const message = error instanceof Error ? error.message : "验证码发送失败";
      set({ error: message });
      throw error;
    }
  },
  verify: async (email, code) => {
    set({ status: "checking", error: null });
    try {
      await verifyCode(email, code);
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
      set({ user: null, status: "anonymous", devCode: null, error: null });
    }
  },
  clearError: () => set({ error: null }),
}));
