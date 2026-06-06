"use client";

import { useCitationPanelStore } from "@/stores/citation-panel-store";
import type { ReportSource } from "@/lib/api/reports";
import { cn } from "@/lib/utils";

interface CitationChipsProps {
  ids: string[];
  sources: ReportSource[];
}

export function CitationChips({ ids, sources }: CitationChipsProps) {
  const open = useCitationPanelStore((s) => s.open);

  if (!ids?.length) return null;

  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-baseline">
      {ids.map((id, index) => {
        const src = sources.find((s) => s.id === id);
        if (!src) return null;
        return (
          <button
            key={`${id}-${index}`}
            type="button"
            onClick={() => open(id)}
            title={src.title}
            aria-label={`查看来源：${src.title}`}
            className={cn(
              "tabular inline-flex items-center rounded-sm border border-border/70 bg-background/80 px-1",
              "text-[10px] uppercase tracking-[0.05em] text-muted-foreground/80",
              "hover:text-foreground hover:border-border hover:bg-background",
              "transition-colors cursor-pointer",
            )}
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {id.replace("src_", "")}
          </button>
        );
      })}
    </span>
  );
}
