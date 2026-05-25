"use client";

import { create } from "zustand";
import type {
  ClarifyingQuestion,
  DimensionSpec,
  TaskScopeContract,
} from "@/lib/mocks/types";

interface ScopingState {
  /** The NL brief the user typed on /tasks/new. */
  userBrief: string;
  /** Competitors the user manually added via chips on /tasks/new. */
  manualCompetitors: string[];
  /** The current draft of the scope contract on /tasks/new/scoping. */
  draftContract: TaskScopeContract | null;
  /** "AI is thinking" flag for the initial generation + regenerate. */
  isGenerating: boolean;

  // --- intake (page 1a) ---
  setUserBrief: (brief: string) => void;
  addManualCompetitor: (name: string) => void;
  removeManualCompetitor: (name: string) => void;
  resetIntake: () => void;

  // --- scoping (page 1b) ---
  setDraftContract: (contract: TaskScopeContract | null) => void;
  setIsGenerating: (flag: boolean) => void;

  // dimension edits
  toggleDimensionEnabled: (id: string) => void;
  updateDimensionTitle: (id: string, title: string) => void;
  updateDimensionIntent: (id: string, intent: string) => void;
  removeDimension: (id: string) => void;
  addExtensionDimension: (title: string, intent: string) => void;
  reorderDimensions: (orderedIds: string[]) => void;

  // competitor edits
  setCompetitors: (names: string[]) => void;
  addCompetitor: (name: string) => void;
  removeCompetitor: (name: string) => void;

  // clarifications
  answerClarification: (id: string, answer: string | null) => void;
}

export const useScopingStore = create<ScopingState>((set) => ({
  userBrief: "",
  manualCompetitors: [],
  draftContract: null,
  isGenerating: false,

  setUserBrief: (brief) => set({ userBrief: brief }),
  addManualCompetitor: (name) =>
    set((s) => {
      const trimmed = name.trim();
      if (!trimmed || s.manualCompetitors.includes(trimmed)) return s;
      return { manualCompetitors: [...s.manualCompetitors, trimmed] };
    }),
  removeManualCompetitor: (name) =>
    set((s) => ({
      manualCompetitors: s.manualCompetitors.filter((c) => c !== name),
    })),
  resetIntake: () =>
    set({ userBrief: "", manualCompetitors: [], draftContract: null }),

  setDraftContract: (contract) => set({ draftContract: contract }),
  setIsGenerating: (flag) => set({ isGenerating: flag }),

  toggleDimensionEnabled: (id) =>
    set((s) => {
      if (!s.draftContract) return s;
      return {
        draftContract: {
          ...s.draftContract,
          dimensions: s.draftContract.dimensions.map((d) =>
            d.id === id && !d.locked ? { ...d, enabled: !d.enabled } : d,
          ),
        },
      };
    }),

  updateDimensionTitle: (id, title) =>
    set((s) => {
      if (!s.draftContract) return s;
      return {
        draftContract: {
          ...s.draftContract,
          dimensions: s.draftContract.dimensions.map((d) =>
            d.id === id ? { ...d, title } : d,
          ),
        },
      };
    }),

  updateDimensionIntent: (id, intent) =>
    set((s) => {
      if (!s.draftContract) return s;
      return {
        draftContract: {
          ...s.draftContract,
          dimensions: s.draftContract.dimensions.map((d) =>
            d.id === id ? { ...d, intent } : d,
          ),
        },
      };
    }),

  removeDimension: (id) =>
    set((s) => {
      if (!s.draftContract) return s;
      return {
        draftContract: {
          ...s.draftContract,
          dimensions: s.draftContract.dimensions.filter(
            (d) => d.id !== id || d.locked,
          ),
        },
      };
    }),

  addExtensionDimension: (title, intent) =>
    set((s) => {
      if (!s.draftContract) return s;
      const slug = `ext.custom_${Date.now()}`;
      const maxOrder = Math.max(
        -1,
        ...s.draftContract.dimensions.map((d) => d.order),
      );
      const newDim: DimensionSpec = {
        id: slug,
        layer: "extension",
        title,
        intent,
        schema_ref: null,
        enabled: true,
        locked: false,
        order: maxOrder + 1,
      };
      return {
        draftContract: {
          ...s.draftContract,
          dimensions: [...s.draftContract.dimensions, newDim],
        },
      };
    }),

  reorderDimensions: (orderedIds) =>
    set((s) => {
      if (!s.draftContract) return s;
      const map = new Map(s.draftContract.dimensions.map((d) => [d.id, d]));
      const reordered = orderedIds
        .map((id, idx) => {
          const d = map.get(id);
          return d ? { ...d, order: idx } : null;
        })
        .filter((d): d is DimensionSpec => d !== null);
      return {
        draftContract: { ...s.draftContract, dimensions: reordered },
      };
    }),

  setCompetitors: (names) =>
    set((s) => {
      if (!s.draftContract) return s;
      return { draftContract: { ...s.draftContract, competitors: names } };
    }),

  addCompetitor: (name) =>
    set((s) => {
      if (!s.draftContract) return s;
      const trimmed = name.trim();
      if (!trimmed || s.draftContract.competitors.includes(trimmed)) return s;
      return {
        draftContract: {
          ...s.draftContract,
          competitors: [...s.draftContract.competitors, trimmed],
        },
      };
    }),

  removeCompetitor: (name) =>
    set((s) => {
      if (!s.draftContract) return s;
      return {
        draftContract: {
          ...s.draftContract,
          competitors: s.draftContract.competitors.filter((c) => c !== name),
        },
      };
    }),

  answerClarification: (id, answer) =>
    set((s) => {
      if (!s.draftContract) return s;
      return {
        draftContract: {
          ...s.draftContract,
          clarifications: s.draftContract.clarifications.map((q: ClarifyingQuestion) =>
            q.id === id ? { ...q, answer } : q,
          ),
        },
      };
    }),
}));
