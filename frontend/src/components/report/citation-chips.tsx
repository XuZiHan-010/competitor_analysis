"use client";

import { useCitationPanelStore } from "@/stores/citation-panel-store";
import type { ReportSource, SourceType } from "@/lib/api/reports";
import { cn } from "@/lib/utils";

interface CitationChipsProps {
  ids: string[];
  sources: ReportSource[];
}

const TYPE_ABBREV: Record<SourceType, string> = {
  official: "官",
  commercial: "商",
  media: "媒",
  user_feedback: "反",
  tech_community: "技",
  user_uploaded: "传",
  published_survey: "调",
  public_review: "公",
  app_review: "评",
  ai_simulated: "AI",
};

export function CitationChips({ ids, sources }: CitationChipsProps) {
  const open = useCitationPanelStore((s) => s.open);

  if (!ids?.length) return null;

  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-baseline">
      {ids.map((id, index) => {
        const src = sources.find((s) => s.id === id);
        if (!src) return null;
        const shortIndex = sources.findIndex((s) => s.id === id);
        const label = shortIndex >= 0 ? `S${shortIndex + 1}` : id.replace("src_", "");
        const typeAbbr = TYPE_ABBREV[src.type] ?? src.type.slice(0, 2);
        return (
          <button
            key={`${id}-${index}`}
            type="button"
            onClick={() => open(id)}
            title={src.title}
            aria-label={`查看来源：${src.title}`}
            className={cn(
              "inline-flex items-center gap-0.5 rounded-sm border border-border/70 bg-background/80 px-1",
              "text-[10px] tracking-[0.04em] text-muted-foreground/80",
              "hover:text-foreground hover:border-border hover:bg-background",
              "transition-colors cursor-pointer",
            )}
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <span className="tabular-nums">{label}</span>
            <span className="text-[9px] text-muted-foreground/50">{typeAbbr}</span>
          </button>
        );
      })}
    </span>
  );
}
