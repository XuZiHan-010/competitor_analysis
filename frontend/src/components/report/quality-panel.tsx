"use client";

import type { ReportClaim, ReportMetrics, ReviewStatus } from "@/lib/api/reports";
import { cn } from "@/lib/utils";

interface QualityPanelProps {
  metrics: ReportMetrics;
  claims: ReportClaim[];
  qaStatus: "passed" | "issues";
  qaIssues: Record<string, unknown>[];
  reviewMode: boolean;
  onToggleReviewMode: () => void;
  onReviewClaim: (claimId: string, status: ReviewStatus) => void;
}

function pct(v: number | null | undefined): string {
  if (v == null) return "-";
  return `${Math.round(v * 100)}%`;
}

function issueText(issue: Record<string, unknown>): string {
  const field = typeof issue.failed_field === "string" ? issue.failed_field : "quality";
  const message = typeof issue.message === "string" ? issue.message : "需要人工复核";
  return `${field}: ${message}`;
}

function metricIssues(metrics: ReportMetrics): Record<string, unknown>[] {
  const raw = metrics.ai_self_assessment.integrity_issues;
  if (!Array.isArray(raw)) return [];
  return raw.filter((item): item is Record<string, unknown> => (
    typeof item === "object" && item !== null && !Array.isArray(item)
  ));
}

function MetricRow({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="min-w-0 text-[12px] leading-snug text-muted-foreground">
        {label}
      </span>
      <span
        className="shrink-0 text-[12px] text-foreground/90 tabular-nums"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {value}
        {sub && <span className="ml-1 text-[10px] text-muted-foreground/70">{sub}</span>}
      </span>
    </div>
  );
}

export function QualityPanel({
  metrics,
  claims,
  qaStatus,
  qaIssues,
  reviewMode,
  onToggleReviewMode,
  onReviewClaim,
}: QualityPanelProps) {
  const pendingReview = claims.filter((c) => c.review_status === "unreviewed").length;
  const editedCount = claims.filter((c) => c.edit_status === "edited").length;
  const integrityIssues = metricIssues(metrics);
  const visibleIssues = [...qaIssues, ...integrityIssues].slice(0, 5);
  const hasIssues = qaStatus === "issues" || visibleIssues.length > 0;
  const reviewableClaims = reviewMode ? claims.slice(0, 6) : [];

  return (
    <aside
      aria-label="报告质量面板"
      className="hidden w-[280px] shrink-0 self-start lg:sticky lg:top-6 lg:flex lg:flex-col"
    >
      <div className="overflow-hidden rounded-md border border-border/60 bg-card/85">
        <div className="border-b border-border/60 px-4 py-3">
          <p
            className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            Quality Gate
          </p>
          {hasIssues && (
            <p className="mt-1.5 text-[12px] leading-snug text-destructive">
              报告含未通过项，不能按满分质量交付。
            </p>
          )}
        </div>

        <div className="space-y-2.5 border-b border-border/60 px-4 py-3">
          <MetricRow label="字段覆盖率" value={pct(metrics.field_coverage_rate)} />
          <MetricRow label="引用覆盖率" value={pct(metrics.citation_coverage_rate)} />
          <MetricRow label="人工修正率" value={pct(metrics.manual_correction_rate)} />
          {metrics.human_verified_accuracy_rate != null && (
            <MetricRow label="人工确认准确率" value={pct(metrics.human_verified_accuracy_rate)} />
          )}
          {metrics.source_support_rate != null && (
            <MetricRow label="来源支撑率" value={pct(metrics.source_support_rate)} />
          )}
        </div>

        {visibleIssues.length > 0 && (
          <div className="space-y-2 border-b border-border/60 bg-destructive/5 px-4 py-3">
            <p
              className="text-[10px] uppercase tracking-[0.15em] text-destructive"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              Blocking Issues
            </p>
            <ul className="space-y-1.5">
              {visibleIssues.map((issue, index) => (
                <li
                  key={`${issueText(issue)}-${index}`}
                  className="break-words text-[11px] leading-relaxed text-foreground/80"
                >
                  {issueText(issue)}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="border-b border-border/60 px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[12px] text-muted-foreground">复核模式</span>
            <button
              type="button"
              role="switch"
              aria-label="切换复核模式"
              aria-checked={reviewMode}
              onClick={onToggleReviewMode}
              className={cn(
                "relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                reviewMode ? "bg-primary" : "bg-border",
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  "inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform duration-150",
                  reviewMode ? "translate-x-4.5" : "translate-x-0.5",
                )}
              />
            </button>
          </div>
          {pendingReview > 0 && (
            <p
              className="mt-1.5 text-[11px] text-muted-foreground/70 tabular-nums"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {pendingReview} 条待复核
            </p>
          )}
          {editedCount > 0 && (
            <p
              className="mt-0.5 text-[11px] text-[var(--color-accent-warm)] tabular-nums"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {editedCount} 处已修正
            </p>
          )}
        </div>

        {reviewMode && reviewableClaims.length > 0 && (
          <div className="space-y-2 px-4 py-3">
            <p
              className="mb-2 text-[10px] uppercase tracking-[0.15em] text-muted-foreground"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              待复核摘要
            </p>
            {reviewableClaims.map((claim) => (
              <div key={claim.id} className="space-y-1">
                <p className="line-clamp-2 text-[11px] leading-snug text-foreground/80">
                  {claim.claim_text}
                </p>
                <div className="flex gap-1">
                  {(["correct", "partial", "wrong", "unverifiable"] as ReviewStatus[]).map(
                    (status) => {
                      const labels: Record<ReviewStatus, string> = {
                        correct: "✓",
                        partial: "◐",
                        wrong: "×",
                        unverifiable: "?",
                        unreviewed: "·",
                      };
                      return (
                        <button
                          key={status}
                          type="button"
                          onClick={() => onReviewClaim(claim.id, status)}
                          aria-label={`标记为 ${status}`}
                          className={cn(
                            "h-6 w-6 rounded border text-[11px] transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                            claim.review_status === status
                              ? "border-primary bg-primary/15 text-primary"
                              : "border-border/60 text-muted-foreground hover:border-border hover:text-foreground",
                          )}
                        >
                          {labels[status]}
                        </button>
                      );
                    },
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
