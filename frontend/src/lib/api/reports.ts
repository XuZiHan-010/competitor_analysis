import type { Lang } from "@/stores/lang-store";
import { apiFetch } from "@/lib/api/client";

// ---------- canonical types (mirror backend schemas/report.py) ----------

export type CorrectionType =
  | "fact_fix"
  | "wording_improvement"
  | "additional_info"
  | "remove_invalid"
  | "structure_adjustment";

export type ReviewStatus =
  | "unreviewed"
  | "correct"
  | "partial"
  | "wrong"
  | "unverifiable";

export interface ReportClaim {
  id: string;
  claim_path: string;
  claim_text: string;
  layer: "core" | "extension" | "survey";
  field_type: "structured" | "free_text";
  source_ids: string[];
  generating_agent: string;
  qa_status: "pass" | "warning" | "blocker";
  source_support: "supported" | "weak" | "unsupported" | "unchecked";
  edit_status: "untouched" | "edited";
  review_status: ReviewStatus;
  correction_type: CorrectionType | null;
}

export interface ReportMetrics {
  analysis_duration_seconds: number | null;
  field_coverage_rate: number;
  citation_coverage_rate: number;
  manual_correction_rate: number;
  human_verified_accuracy_rate: number | null;
  source_support_rate: number | null;
  source_type_coverage_rate: number | null;
  invalid_source_rate: number | null;
  rerun_rate: number | null;
  correction_type_breakdown: Record<string, number>;
  ai_self_assessment: Record<string, unknown>;
}

export interface ReportSource {
  id: string;
  url: string;
  title: string;
  snippet: string;
  category: string;
  valid: boolean;
}

// --- structured_content canonical shape (after WriterAgent fix) ---

export interface FeatureCell {
  competitor: string;
  status: "supported" | "partial" | "unsupported" | "unknown";
  note?: string;
}

export interface FeatureRow {
  feature: string;
  description?: string;
  cells: FeatureCell[];
  source_ids: string[];
}

export interface PricingTier {
  competitor: string;
  tier: string;
  price: string;
  highlights: string[];
  source_ids: string[];
}

export interface Persona {
  competitor: string;
  label: string;
  size: "majority" | "significant" | "niche";
  needs: string[];
  pain_points: string[];
  evidence: string;
  source_ids: string[];
}

export interface SwotItem {
  text: string;
  source_ids: string[];
}

export interface SwotBlock {
  competitor: string;
  strengths: SwotItem[];
  weaknesses: SwotItem[];
  opportunities: SwotItem[];
  threats: SwotItem[];
}

export interface ExtensionBullet {
  competitor: string;
  points: string[];
  source_ids: string[];
}

export interface ExtensionSection {
  dimension_id: string;
  title: string;
  intent: string;
  summary: string;
  bullets: ExtensionBullet[];
}

export interface SurveyEvidence {
  id: string;
  source_type: "user_uploaded_primary" | "published_survey" | "public_review" | "ai_simulated";
  content: string;
  redacted: boolean;
}

export interface SurveyInsight {
  point: string;
  confidence: "high" | "medium" | "low";
  evidence_ids: string[];
}

export interface SurveyResult {
  competitor_name: string;
  evidence: SurveyEvidence[];
  insights: SurveyInsight[];
  source_breakdown: Record<string, number>;
}

export interface StructuredContent {
  title: string;
  subtitle: string;
  summary: string;
  language: string;
  competitors: string[];
  feature_tree: { intro: string; rows: FeatureRow[] };
  pricing: { intro: string; tiers: PricingTier[] };
  user_personas: { intro: string; personas: Persona[] };
  swot: { intro: string; blocks: SwotBlock[] };
  extensions: ExtensionSection[];
  cross_analysis: {
    feature_matrix?: { rows: FeatureRow[]; competitors: string[] };
    pricing_comparison?: Record<string, unknown>;
    positioning_map?: {
      x_axis: string;
      y_axis: string;
      competitors: { id: string; x: number; y: number; label: string }[];
    };
    differentiation_summary?: string;
  };
  survey: SurveyResult[];
}

export interface Report {
  id: string;
  task_id: string;
  language: "zh" | "en";
  structured_content: StructuredContent;
  markdown_content: string;
  sources: ReportSource[];
  claims: ReportClaim[];
  metrics: ReportMetrics;
  qa_status: "passed" | "issues";
  qa_issues: Record<string, unknown>[];
  created_at: string;
}

// ---------- API functions ----------

export async function fetchReport(taskId: string): Promise<Report> {
  const res = await apiFetch(`/api/reports/${taskId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`fetchReport ${res.status}`);
  return res.json() as Promise<Report>;
}

export async function fetchReportMetrics(taskId: string): Promise<ReportMetrics> {
  const res = await apiFetch(`/api/reports/${taskId}/metrics`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`fetchReportMetrics ${res.status}`);
  return res.json() as Promise<ReportMetrics>;
}

export async function correctSection(
  taskId: string,
  payload: {
    claim_id: string;
    field_path: string;
    new_value: string;
    correction_type: CorrectionType;
    triggered_rerun?: boolean;
  },
): Promise<Report> {
  const res = await apiFetch(`/api/reports/${taskId}/field`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`correctSection ${res.status}`);
  return res.json() as Promise<Report>;
}

export async function reviewClaim(
  taskId: string,
  claimId: string,
  status: ReviewStatus,
): Promise<Report> {
  const res = await apiFetch(
    `/api/reports/${taskId}/claims/${claimId}/review`,
    {
      method: "PATCH",
      body: JSON.stringify({ review_status: status }),
    },
  );
  if (!res.ok) throw new Error(`reviewClaim ${res.status}`);
  return res.json() as Promise<Report>;
}

export async function exportReport(
  taskId: string,
  format: "pdf" | "markdown",
): Promise<Blob> {
  const res = await apiFetch(
    `/api/reports/${taskId}/export?format=${format}`,
  );
  if (!res.ok) throw new Error(`exportReport ${res.status}`);
  return res.blob();
}

export async function switchReportLanguage(taskId: string, language: Lang): Promise<Report> {
  const res = await apiFetch(`/api/reports/${taskId}/language`, {
    method: "POST",
    body: JSON.stringify({ language }),
  });
  if (!res.ok) throw new Error(`switchReportLanguage ${res.status}`);
  return res.json() as Promise<Report>;
}

// ---------- historical report semantic search (mirror schemas/report.py) ----------

export type ReportSearchMode = "pgvector" | "in_memory_semantic_fallback";

export interface ReportSearchResultItem {
  report_id: string;
  task_id: string;
  language: "zh" | "en";
  title: string;
  snippet: string;
  claim_ids: string[];
  source_ids: string[];
}

export interface ReportSearchResponse {
  query: string;
  mode: ReportSearchMode;
  results: ReportSearchResultItem[];
}

export async function searchReports(q: string, limit = 10): Promise<ReportSearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  const res = await apiFetch(`/api/reports/search?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`searchReports ${res.status}`);
  return res.json() as Promise<ReportSearchResponse>;
}
