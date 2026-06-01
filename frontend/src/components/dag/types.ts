/**
 * Shared view model for the agent DAG, consumed by both the live task page
 * (`/tasks/[id]`) and the demo replay page (`/demo/run`). Components in this
 * folder are presentational and props-only — they never import data sources,
 * so the Route Isolation Contract (PRD §十一-quater 11Q.7) holds.
 */

export type AgentNodeStatus =
  | "idle"
  | "running"
  | "done"
  | "failed"
  /** QA flagged a blocker — transient, not a hard error. */
  | "warn"
  /** Collector re-running after a QA打回 (Evaluator-Optimizer loop). */
  | "retrying";

export interface DagNodeView {
  /** Canonical agent name, e.g. "CollectorAgent". */
  agent: string;
  /** Short display label, e.g. "Collector". */
  label: string;
  /** One-line role description shown under the label. */
  role: string;
  status: AgentNodeStatus;
  /** Number of times this node was re-run via the feedback loop (0 = never). */
  retryCount: number;
}
