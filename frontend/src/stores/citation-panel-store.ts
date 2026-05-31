"use client";

import { create } from "zustand";

interface CitationPanelState {
  openSourceId: string | null;
  open: (sourceId: string) => void;
  close: () => void;
}

export const useCitationPanelStore = create<CitationPanelState>((set) => ({
  openSourceId: null,
  open: (sourceId) => {
    set({ openSourceId: sourceId });
    if (typeof window !== "undefined") {
      window.location.hash = `citation=${sourceId}`;
    }
  },
  close: () => {
    set({ openSourceId: null });
    if (typeof window !== "undefined") {
      history.pushState(null, "", window.location.pathname + window.location.search);
    }
  },
}));
