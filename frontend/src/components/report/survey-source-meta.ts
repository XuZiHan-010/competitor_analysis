import type { SurveyEvidence } from "@/lib/api/reports";

export type SurveySourceType = SurveyEvidence["source_type"];

export interface SurveySourceMeta {
  label: string;
  /** Short glyph shown in badges/legend. */
  glyph: string;
  /** oklch color used for the stacked bar segment, legend dot, and badge. */
  color: string;
}

/**
 * Data-source trust tiers for the 方案 C user-research module (PRD §六 5.4).
 * Order is most-trusted → least-trusted; the stacked bar renders in this order
 * so `ai_simulated` (lowest trust, fallback only) always lands on the right.
 * `ai_simulated` deliberately reuses --color-accent-warm — the system's
 * "caution / AI" color — so simulated data reads as provisional everywhere.
 */
export const SURVEY_SOURCE_ORDER: SurveySourceType[] = [
  "user_uploaded_primary",
  "published_survey",
  "public_review",
  "ai_simulated",
];

export const SURVEY_SOURCE_META: Record<SurveySourceType, SurveySourceMeta> = {
  user_uploaded_primary: {
    label: "一手上传",
    glyph: "✓",
    color: "oklch(0.62 0.17 145)",
  },
  published_survey: {
    label: "公开调研",
    glyph: "▤",
    color: "oklch(0.55 0.15 250)",
  },
  public_review: {
    label: "公开评论",
    glyph: "❝",
    color: "oklch(0.55 0.18 300)",
  },
  ai_simulated: {
    label: "AI 模拟",
    glyph: "⚠",
    color: "var(--color-accent-warm)",
  },
};

/** Fraction (0–1) of evidence/breakdown that is AI-simulated. */
export function aiSimulatedShare(breakdown: Record<string, number>): number {
  const total = Object.values(breakdown).reduce((sum, n) => sum + n, 0);
  if (total === 0) return 0;
  return (breakdown.ai_simulated ?? 0) / total;
}
