"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Lang = "zh" | "en";

interface LangState {
  lang: Lang;
  setLang: (lang: Lang) => void;
  toggle: () => void;
}

export const useLangStore = create<LangState>()(
  persist(
    (set) => ({
      lang: "zh",
      setLang: (lang) => set({ lang }),
      toggle: () => set((s) => ({ lang: s.lang === "zh" ? "en" : "zh" })),
    }),
    { name: "strata-lang" },
  ),
);
