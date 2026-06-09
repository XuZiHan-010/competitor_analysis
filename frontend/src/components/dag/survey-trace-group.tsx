"use client";

import { useId, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { AgentTrace } from "@/lib/api/tasks";
import { cn } from "@/lib/utils";
import { TraceRow } from "./trace-row";

/**
 * SurveyTool is a sub-workflow nested inside the Collector node, so its
 * per-stage / per-competitor traces (7 stages × N competitors) would otherwise
 * flood the flat timeline and bury the four top-level agents. We fold them into
 * a single collapsible group anchored at their sequence position, showing only
 * a one-line rollup until expanded. Body height animates via the grid-rows
 * 0fr→1fr technique to match CollapsibleSection.
 */
export function SurveyTraceGroup({ traces }: { traces: AgentTrace[] }) {
  const [open, setOpen] = useState(false);
  const bodyId = useId();

  const failed = traces.filter((t) => t.status === "failed").length;
  const seqStart = traces[0]?.sequence_no;
  const seqEnd = traces[traces.length - 1]?.sequence_no;
  const seqLabel =
    seqStart === seqEnd ? `#${seqStart}` : `#${seqStart}–${seqEnd}`;

  return (
    <li className="overflow-hidden rounded-md border border-border/60 bg-card/50">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex w-full items-center justify-between gap-3 px-4 py-3 text-left",
          "transition-colors hover:bg-card/70",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        )}
      >
        <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span
            className="tabular text-[10px] uppercase tracking-[0.16em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {seqLabel}
          </span>
          <span className="text-sm text-foreground">SurveyTool</span>
          <span className="text-xs text-muted-foreground">
            Collector 子流程 · {traces.length} 条
            {failed > 0 && (
              <span className="text-[var(--color-accent-warm)]">
                {" "}· {failed} 失败
              </span>
            )}
          </span>
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
            open && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>

      <div
        id={bodyId}
        className={cn(
          "grid transition-[grid-template-rows] duration-200 ease-out",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <ol className="space-y-2 border-t border-border/60 px-3 py-3">
            {traces.map((trace) => (
              <TraceRow key={trace.id} trace={trace} />
            ))}
          </ol>
        </div>
      </div>
    </li>
  );
}
