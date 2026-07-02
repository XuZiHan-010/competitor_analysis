/**
 * Shapes for the curated demo playback under `/demo/*`.
 *
 * These mirror PRD §十一Q.3. They are NOT canonical Pydantic mirrors —
 * the real backend payloads (once Stage 2 lands) will be shaped by the
 * LangGraph state and may differ. The demo fixtures we ship in this folder
 * are scaffold-grade pre-records used until a real run is captured.
 */

import type { TaskScopeContract } from "@/lib/mocks/types";

export type DemoAgent =
  | "ScopingAgent"
  | "CollectorAgent"
  | "AnalystAgent"
  | "WriterAgent"
  | "QAAgent";

export type DemoNodeStatus = "idle" | "running" | "ok" | "warn";

/** One event in the DAG playback trace. */
export interface DemoTraceEvent {
  /** Milliseconds since playback start. Events fire in ascending order. */
  ts_offset_ms: number;
  agent: DemoAgent;
  /**
   * One of:
   * - "start" / "complete" — node lifecycle, drives DAG circle status
   * - "tool_call" / "tool_result" — payload describes external action
   * - "blocker" / "resolved" — QA feedback loop, surfaced in trace panel
   * - "note" — neutral commentary, only shown in trace
   */
  event:
    | "start"
    | "complete"
    | "tool_call"
    | "tool_result"
    | "blocker"
    | "resolved"
    | "note";
  /** Free-form short payload shown in the right-hand trace list. */
  payload: string;
}

export interface DemoSource {
  id: string;
  type: "url" | "document" | "simulated_survey";
  url: string;
  title: string;
  /** Excerpt shown when the citation chip is expanded. */
  snippet: string;
  agent: DemoAgent;
  fetched_at: string;
  /** Authority tier A>B>C (see components/report/source-tier). Absent → shown as C. */
  tier?: "A" | "B" | "C" | null;
}

export interface DemoFeatureSupport {
  competitor: string;
  status: "supported" | "partial" | "unsupported" | "unknown";
  note?: string;
}

export interface DemoFeatureRow {
  feature: string;
  description: string;
  cells: DemoFeatureSupport[];
  source_ids: string[];
}

export interface DemoPricingTier {
  competitor: string;
  tier: string;
  /** Original string (with units / currency) preserved. */
  price: string;
  highlights: string[];
  source_ids: string[];
}

export interface DemoPersona {
  competitor: string;
  label: string;
  size: "majority" | "significant" | "niche";
  needs: string[];
  pain_points: string[];
  evidence: string;
  source_ids: string[];
}

export interface DemoSwotBlock {
  competitor: string;
  strengths: { text: string; source_ids: string[] }[];
  weaknesses: { text: string; source_ids: string[] }[];
  opportunities: { text: string; source_ids: string[] }[];
  threats: { text: string; source_ids: string[] }[];
}

export interface DemoExtensionSection {
  dimension_id: string;
  title: string;
  intent: string;
  summary: string;
  bullets: { competitor: string; points: string[]; source_ids: string[] }[];
}

export interface DemoCrossAnalysis {
  feature_matrix: DemoFeatureRow[];
  positioning_map: {
    x_axis: string;
    y_axis: string;
    competitors: { id: string; x: number; y: number; label: string }[];
  };
  differentiation_summary: string;
}

export interface DemoReport {
  task_id: string;
  title: string;
  subtitle: string;
  generated_at: string;
  competitors: string[];
  /** Chapter 1 — feature tree, as a matrix across competitors. */
  feature_tree: { intro: string; rows: DemoFeatureRow[] };
  /** Chapter 2 — pricing model rows across competitors. */
  pricing: { intro: string; tiers: DemoPricingTier[] };
  /** Chapter 3 — user persona blocks (one per competitor). */
  user_personas: { intro: string; personas: DemoPersona[] };
  /** Chapter 4 — SWOT per competitor. */
  swot: { intro: string; blocks: DemoSwotBlock[] };
  /** Chapters 5+ — AI-suggested extension sections (≤ 4). */
  extensions: DemoExtensionSection[];
  cross_analysis: DemoCrossAnalysis;
}

export interface DemoBundle {
  scope: TaskScopeContract;
  trace: DemoTraceEvent[];
  report: DemoReport;
  sources: DemoSource[];
}
