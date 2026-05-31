import type { SwotBlock as SwotBlockType, ReportSource } from "@/lib/api/reports";
import { CitationChips } from "./citation-chips";

interface SwotBlockProps {
  block: SwotBlockType;
  sources: ReportSource[];
}

const QUADS: { key: keyof Omit<SwotBlockType, "competitor">; label: string }[] = [
  { key: "strengths", label: "Strengths" },
  { key: "weaknesses", label: "Weaknesses" },
  { key: "opportunities", label: "Opportunities" },
  { key: "threats", label: "Threats" },
];

export function SwotBlock({ block, sources }: SwotBlockProps) {
  return (
    <article className="rounded-md border border-border/60 bg-card/60 p-5">
      <p
        className="text-[1.05rem] mb-4 text-foreground/95"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {block.competitor}
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {QUADS.map((q) => {
          const items = block[q.key];
          return (
            <div key={q.key}>
              <p
                className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-2"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {q.label}
              </p>
              <ul className="space-y-1.5 text-[12.5px] text-foreground/90 leading-relaxed">
                {items.map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span aria-hidden="true" className="text-muted-foreground/70 mt-1 shrink-0">
                      —
                    </span>
                    <span>
                      {item.text}
                      <CitationChips ids={item.source_ids} sources={sources} />
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </article>
  );
}
