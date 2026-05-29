import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  aiSimulatedShare,
  SURVEY_SOURCE_META,
  SURVEY_SOURCE_ORDER,
  type SurveySourceType,
} from "./survey-source-meta";

/** Above this AI-simulated share, surface a top-of-section caution banner. */
const AI_WARN_THRESHOLD = 0.6;

/**
 * Horizontal stacked bar of evidence provenance for one competitor. Always
 * expanded (judges won't click to reveal) and, when AI-simulated evidence
 * dominates, prefixed with a caution banner — the compliance requirement from
 * PRD §六 5.4 / the Survey 修订清单.
 */
export function SurveySourceBreakdown({
  breakdown,
}: {
  breakdown: Record<string, number>;
}) {
  const total = Object.values(breakdown).reduce((sum, n) => sum + n, 0);
  if (total === 0) return null;

  const segments = SURVEY_SOURCE_ORDER.map((type) => ({
    type,
    count: breakdown[type] ?? 0,
    pct: Math.round(((breakdown[type] ?? 0) / total) * 100),
  })).filter((s) => s.count > 0);

  const aiShare = aiSimulatedShare(breakdown);
  const aiOverThreshold = aiShare > AI_WARN_THRESHOLD;

  return (
    <div className="space-y-2.5">
      {aiOverThreshold && (
        <div className="flex items-start gap-2 rounded-md border border-[var(--color-accent-warm)]/40 bg-[var(--color-accent-warm)]/10 px-3 py-2">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--color-accent-warm)]" />
          <p className="text-[12px] leading-relaxed text-[var(--color-accent-warm)]">
            本区块超过 {Math.round(aiShare * 100)}% 的证据来自 AI 模拟答卷，仅供参考，不能替代真实用户调研。
          </p>
        </div>
      )}

      <div
        role="img"
        aria-label={`数据来源分布：${segments
          .map((s) => `${SURVEY_SOURCE_META[s.type].label} ${s.pct}%`)
          .join("，")}`}
        className="flex h-5 overflow-hidden rounded-[5px]"
      >
        {segments.map((s) => (
          <div
            key={s.type}
            className="flex items-center justify-center"
            style={{ width: `${s.pct}%`, backgroundColor: SURVEY_SOURCE_META[s.type].color }}
            title={`${SURVEY_SOURCE_META[s.type].label} ${s.pct}%`}
          >
            {s.pct >= 12 && (
              <span className="px-1 text-[10px] font-medium tabular text-white/95">
                {s.pct}%
              </span>
            )}
          </div>
        ))}
      </div>

      <ul className="flex flex-wrap gap-x-4 gap-y-1.5">
        {segments.map((s) => (
          <LegendItem key={s.type} type={s.type} count={s.count} pct={s.pct} />
        ))}
      </ul>
    </div>
  );
}

function LegendItem({
  type,
  count,
  pct,
}: {
  type: SurveySourceType;
  count: number;
  pct: number;
}) {
  const meta = SURVEY_SOURCE_META[type];
  const isAi = type === "ai_simulated";
  return (
    <li className="flex items-center gap-1.5 text-[11px]">
      <span
        aria-hidden="true"
        className="inline-block h-2.5 w-2.5 rounded-[3px]"
        style={{ backgroundColor: meta.color }}
      />
      <span className={cn("text-muted-foreground", isAi && "text-[var(--color-accent-warm)]")}>
        {meta.label}
      </span>
      <span className="tabular text-muted-foreground/60">
        {pct}% · {count} 条
      </span>
    </li>
  );
}
