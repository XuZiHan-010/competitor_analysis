import type { Persona, ReportSource } from "@/lib/api/reports";
import { CitationChips } from "./citation-chips";

interface PersonaCardProps {
  persona: Persona;
  sources: ReportSource[];
}

export function PersonaCard({ persona, sources }: PersonaCardProps) {
  return (
    <article className="rounded-md border border-border/60 bg-card/60 p-5">
      <p
        className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {persona.competitor} · {persona.size}
      </p>
      <p
        className="text-[1.05rem] my-2 text-foreground/95 leading-snug"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {persona.label}
      </p>

      <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground mt-3 mb-1">
        需求
      </p>
      <ul className="text-[12.5px] text-foreground/90 leading-relaxed space-y-0.5 mb-3">
        {persona.needs.map((n, i) => (
          <li key={i}>· {n}</li>
        ))}
      </ul>

      <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground mb-1">
        痛点
      </p>
      <ul className="text-[12.5px] text-foreground/90 leading-relaxed space-y-0.5 mb-3">
        {persona.pain_points.map((p, i) => (
          <li key={i}>· {p}</li>
        ))}
      </ul>

      {persona.evidence && (
        <blockquote
          className="border-l-2 border-[var(--color-accent-warm)] pl-3 mt-3 text-[12px] italic text-foreground/80 leading-relaxed"
          style={{ fontFamily: "var(--font-display)" }}
        >
          &ldquo;{persona.evidence}&rdquo;
        </blockquote>
      )}
      <CitationChips ids={persona.source_ids} sources={sources} />
    </article>
  );
}
