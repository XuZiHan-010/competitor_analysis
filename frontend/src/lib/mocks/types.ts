/**
 * TypeScript mirrors of PRD §七 7.0 (TaskScopeContract) and 7.7 (ExtensionFinding).
 *
 * IMPORTANT: keep these in lockstep with docs/PRD.md. When backend Pydantic
 * models are added at apps/api/schemas/, regenerate these via openapi-typescript
 * or maintain manually. Until then this file is the front-end source of truth.
 */

export type DimensionLayer = "core" | "extension";
export type DimensionSource = "system" | "ai_suggested" | "user_added";

export interface DimensionSpec {
  /** Stable id. core layer uses "core.<schema>", extension uses "ext.<slug>" */
  id: string;
  layer: DimensionLayer;
  /**
   * Provenance — see PRD §七 7.0 invariants.
   * - "system": locked core dimensions
   * - "ai_suggested": ScopingAgent proposed (≤4 per task)
   * - "user_added": user manually added on the outline page (no cap)
   */
  source: DimensionSource;
  /** User-editable section title rendered in the report TOC */
  title: string;
  /**
   * Per-language default titles for system/ai dimensions.
   * When present, the UI renders title_i18n[lang] instead of title.
   * Cleared when the user manually edits the title (user takes ownership).
   */
  title_i18n?: Partial<Record<"zh" | "en", string>>;
  /** User-editable one-line description that steers Analyst prompts */
  intent: string;
  /**
   * Per-language default intents for system/ai dimensions.
   * Same ownership semantics as title_i18n.
   */
  intent_i18n?: Partial<Record<"zh" | "en", string>>;
  /** Points at a core schema name ("FeatureTree" etc.) or null for extension */
  schema_ref: string | null;
  /** User checkbox state. Core layer is forced true. */
  enabled: boolean;
  /** Core layer is true, UI disables the delete button. */
  locked: boolean;
  /** Order in the report TOC. Core and extension may interleave. */
  order: number;
}

export interface ClarifyingQuestion {
  id: string;
  question: string;
  /** Single-choice options the user picks from chips. */
  options: string[];
  /** null until answered (questions are skippable). */
  answer: string | null;
}

export interface TaskScopeContract {
  task_id: string;
  /** User's own product name (optional). */
  target_product: string | null;
  /** Confirmed competitor list (NL-extracted + chip-merged + deduped). */
  competitors: string[];
  /** Original NL brief, preserved for backtracking. */
  user_brief: string;
  /** AI's clarifying questions and user's (optional) answers. */
  clarifications: ClarifyingQuestion[];
  /** The outline. Core 4 + N extensions, in user-chosen order. */
  dimensions: DimensionSpec[];
  /** ISO timestamp once the user confirms "Begin analysis". null until frozen. */
  frozen_at: string | null;
}

/** Stable IDs for the 4 mandatory core dimensions, matching PRD §七 7.1-7.4. */
export const CORE_DIMENSION_IDS = {
  FEATURE_TREE: "core.feature_tree",
  PRICING_MODEL: "core.pricing_model",
  USER_PERSONA: "core.user_persona",
  SWOT: "core.swot",
} as const;
