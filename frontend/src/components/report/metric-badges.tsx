import type { ReportMetrics } from "@/lib/api/reports";
import { cn } from "@/lib/utils";

interface MetricBadgesProps {
  metrics: ReportMetrics;
}

function pct(v: number | null | undefined) {
  if (v == null) return "—";
  return `${Math.round(v * 100)}%`;
}

function dur(secs: number | null | undefined) {
  if (secs == null) return "—";
  return secs < 60 ? `${Math.round(secs)}s` : `${(secs / 60).toFixed(1)}min`;
}

interface BadgeProps {
  label: string;
  value: string;
  tone?: "good" | "warn" | "neutral";
}

function Badge({ label, value, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-1.5 px-2.5 py-1 rounded border text-[11px]",
        tone === "good" && "border-primary/30 bg-primary/6 text-primary",
        tone === "warn" && "border-[var(--color-accent-warm)]/40 bg-[var(--color-accent-warm)]/8 text-[var(--color-accent-warm)]",
        tone === "neutral" && "border-border/70 bg-card/80 text-foreground/70",
      )}
    >
      <span style={{ fontFamily: "var(--font-mono)" }} className="tabular">
        {value}
      </span>
      <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </span>
    </span>
  );
}

export function MetricBadges({ metrics }: MetricBadgesProps) {
  const fieldCov = metrics.field_coverage_rate;
  const citCov = metrics.citation_coverage_rate;

  return (
    <div className="flex flex-wrap items-center gap-2" role="list" aria-label="报告质量指标">
      <Badge
        label="字段覆盖"
        value={pct(fieldCov)}
        tone={fieldCov >= 0.9 ? "good" : fieldCov >= 0.7 ? "warn" : "neutral"}
      />
      <Badge
        label="引用覆盖"
        value={pct(citCov)}
        tone={citCov >= 0.85 ? "good" : citCov >= 0.6 ? "warn" : "neutral"}
      />
      {metrics.source_type_coverage_rate != null && (
        <Badge label="信源类型" value={pct(metrics.source_type_coverage_rate)} />
      )}
      <Badge label="耗时" value={dur(metrics.analysis_duration_seconds)} />
    </div>
  );
}
