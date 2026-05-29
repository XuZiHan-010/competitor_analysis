"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { SurveyEvidence, SurveyResult } from "@/lib/api/reports";
import { SurveySourceBreakdown } from "./survey-source-breakdown";
import { SurveyInsightCard } from "./survey-insight-card";

/**
 * "用户声音洞察" report section (方案 C user-research module). Renders one
 * competitor at a time via tabs, leading with the evidence-provenance bar so
 * the trust mix is the first thing a reviewer sees. Returns null when there is
 * no survey data so the report simply omits the section.
 */
export function SurveySection({ results }: { results: SurveyResult[] }) {
  const [active, setActive] = useState(0);
  if (results.length === 0) return null;

  const current = results[Math.min(active, results.length - 1)];
  const evidenceById = new Map<string, SurveyEvidence>(
    current.evidence.map((e) => [e.id, e]),
  );

  return (
    <section className="mt-14" aria-labelledby="survey-title">
      <p
        className="mb-2 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        Survey · 用户声音
      </p>
      <h2
        id="survey-title"
        className="mb-6 text-[1.8rem] leading-[1.1] tracking-tight text-foreground"
        style={{
          fontFamily: "var(--font-display)",
          fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
          fontWeight: 400,
        }}
      >
        用户研究洞察
      </h2>

      {results.length > 1 && (
        <div
          role="tablist"
          aria-label="竞品切换"
          className="mb-5 flex flex-wrap gap-1.5 border-b border-border/60"
        >
          {results.map((r, i) => (
            <button
              key={r.competitor_name + i}
              role="tab"
              type="button"
              aria-selected={i === active}
              onClick={() => setActive(i)}
              className={cn(
                "-mb-px border-b-2 px-3 py-2 text-sm transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                i === active
                  ? "border-foreground text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground/80",
              )}
              style={{ fontFamily: "var(--font-display)" }}
            >
              {r.competitor_name}
            </button>
          ))}
        </div>
      )}

      <article className="overflow-hidden rounded-md border border-border/60 bg-card/40">
        <div className="border-b border-border/60 px-5 py-4">
          {results.length === 1 && (
            <p
              className="mb-3 text-[1.05rem] text-foreground/95"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {current.competitor_name}
            </p>
          )}
          <SurveySourceBreakdown breakdown={current.source_breakdown} />
        </div>

        {current.insights.length > 0 && (
          <div className="px-5 py-4">
            <p
              className="mb-3 text-[10px] uppercase tracking-[0.18em] text-muted-foreground"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              洞察
            </p>
            <ul className="space-y-2.5">
              {current.insights.map((insight, i) => (
                <SurveyInsightCard key={i} insight={insight} evidence={evidenceById} />
              ))}
            </ul>
          </div>
        )}
      </article>
    </section>
  );
}
