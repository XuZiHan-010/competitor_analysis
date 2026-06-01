import { cn } from "@/lib/utils";
import type { SurveyEvidence, SurveyInsight } from "@/lib/api/reports";
import { SURVEY_SOURCE_META } from "./survey-source-meta";

const CONFIDENCE_TONE: Record<SurveyInsight["confidence"], string> = {
  high: "border-primary/40 text-primary",
  medium: "border-[var(--color-accent-warm)]/40 text-[var(--color-accent-warm)]",
  low: "border-border/60 text-muted-foreground/70",
};

const CONFIDENCE_LABEL: Record<SurveyInsight["confidence"], string> = {
  high: "高置信",
  medium: "中置信",
  low: "低置信",
};

/**
 * One survey insight with its confidence tier and the provenance of the
 * evidence backing it. Any insight resting on AI-simulated evidence carries a
 * visible ⚠ AI 模拟 badge so reviewers never mistake it for real user voice.
 */
export function SurveyInsightCard({
  insight,
  evidence,
}: {
  insight: SurveyInsight;
  /** Evidence rows for this competitor, indexed by id for lookup. */
  evidence: Map<string, SurveyEvidence>;
}) {
  const linked = insight.evidence_ids
    .map((id) => evidence.get(id))
    .filter((e): e is SurveyEvidence => e !== undefined);

  // Distinct source types backing this insight, in trust order (meta order).
  const sourceTypes = Array.from(new Set(linked.map((e) => e.source_type)));
  const hasSimulated = sourceTypes.includes("ai_simulated");

  return (
    <li className="rounded-md border border-border/60 bg-card/50 px-4 py-3">
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-[0.1em]",
            CONFIDENCE_TONE[insight.confidence],
          )}
          style={{ fontFamily: "var(--font-mono)" }}
          title={`置信度：${insight.confidence}`}
        >
          {CONFIDENCE_LABEL[insight.confidence]}
        </span>
        <p className="text-[13.5px] leading-relaxed text-foreground/90">{insight.point}</p>
      </div>

      {sourceTypes.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5 pl-[3.25rem]">
          {sourceTypes.map((type) => {
            const meta = SURVEY_SOURCE_META[type];
            const isAi = type === "ai_simulated";
            return (
              <span
                key={type}
                className={cn(
                  "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px]",
                  isAi
                    ? "bg-[var(--color-accent-warm)]/15 font-medium text-[var(--color-accent-warm)]"
                    : "border border-border/50 text-muted-foreground/80",
                )}
              >
                <span aria-hidden="true">{meta.glyph}</span>
                {isAi ? "AI 模拟" : meta.label}
              </span>
            );
          })}
        </div>
      )}

      {hasSimulated && (
        <p className="mt-1.5 pl-[3.25rem] text-[10.5px] leading-snug text-[var(--color-accent-warm)]/80">
          ⚠ 含 AI 模拟答卷推断，非真实用户反馈
        </p>
      )}
    </li>
  );
}
