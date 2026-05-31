"use client";

import type { ReportMetrics, ReportClaim, ReviewStatus } from "@/lib/api/reports";
import { cn } from "@/lib/utils";

interface QualityPanelProps {
  metrics: ReportMetrics;
  claims: ReportClaim[];
  reviewMode: boolean;
  onToggleReviewMode: () => void;
  onReviewClaim: (claimId: string, status: ReviewStatus) => void;
}

function pct(v: number | null | undefined) {
  if (v == null) return "—";
  return `${Math.round(v * 100)}%`;
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
      <span className="text-[12px] text-muted-foreground leading-snug">{label}</span>
      <span className="tabular text-[12px] text-foreground/90 shrink-0" style={{ fontFamily: "var(--font-mono)" }}>
        {value}
        {sub && (
          <span className="text-[10px] text-muted-foreground/70 ml-1">{sub}</span>
        )}
      </span>
    </div>
  );
}

export function QualityPanel({
  metrics,
  claims,
  reviewMode,
  onToggleReviewMode,
  onReviewClaim,
}: QualityPanelProps) {
  const pendingReview = claims.filter((c) => c.review_status === "unreviewed").length;
  const editedCount = claims.filter((c) => c.edit_status === "edited").length;

  const reviewableClaims = reviewMode ? claims.slice(0, 6) : [];

  return (
    <aside
      aria-label="质量面板"
      className="w-[280px] shrink-0 hidden lg:flex flex-col gap-0 self-start sticky top-6"
    >
      <div className="rounded-md border border-border/60 bg-card/80 overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-border/60">
          <p
            className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            质量面板
          </p>
        </div>

        {/* Metrics */}
        <div className="px-4 py-3 space-y-2.5 border-b border-border/60">
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

        {/* Review mode toggle */}
        <div className="px-4 py-3 border-b border-border/60">
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground">复核模式</span>
            <button
              role="switch"
              aria-checked={reviewMode}
              onClick={onToggleReviewMode}
              className={cn(
                "relative inline-flex h-5 w-9 items-center rounded-full transition-colors",
                reviewMode ? "bg-primary" : "bg-border",
              )}
            >
              <span
                className={cn(
                  "inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform",
                  reviewMode ? "translate-x-4.5" : "translate-x-0.5",
                )}
              />
              <span className="sr-only">{reviewMode ? "关闭复核模式" : "开启复核模式"}</span>
            </button>
          </div>
          {pendingReview > 0 && (
            <p className="text-[11px] text-muted-foreground/70 mt-1.5" style={{ fontFamily: "var(--font-mono)" }}>
              {pendingReview} 条待复核
            </p>
          )}
          {editedCount > 0 && (
            <p className="text-[11px] text-[var(--color-accent-warm)] mt-0.5" style={{ fontFamily: "var(--font-mono)" }}>
              {editedCount} 处已修正
            </p>
          )}
        </div>

        {/* Review mode claim list */}
        {reviewMode && reviewableClaims.length > 0 && (
          <div className="px-4 py-3 space-y-2">
            <p
              className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground mb-2"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              待复核摘要
            </p>
            {reviewableClaims.map((claim) => (
              <div key={claim.id} className="space-y-1">
                <p className="text-[11px] text-foreground/80 leading-snug line-clamp-2">
                  {claim.claim_text}
                </p>
                <div className="flex gap-1">
                  {(["correct", "partial", "wrong", "unverifiable"] as ReviewStatus[]).map(
                    (s) => {
                      const labels: Record<ReviewStatus, string> = {
                        correct: "✓",
                        partial: "◑",
                        wrong: "✗",
                        unverifiable: "?",
                        unreviewed: "·",
                      };
                      return (
                        <button
                          key={s}
                          onClick={() => onReviewClaim(claim.id, s)}
                          aria-label={s}
                          className={cn(
                            "h-6 w-6 text-[11px] rounded border transition-colors",
                            claim.review_status === s
                              ? "border-primary bg-primary/15 text-primary"
                              : "border-border/60 text-muted-foreground hover:border-border hover:text-foreground",
                          )}
                        >
                          {labels[s]}
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
