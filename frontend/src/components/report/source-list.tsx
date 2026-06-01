import { ExternalLink } from "lucide-react";
import type { ReportSource } from "@/lib/api/reports";

interface SourceListProps {
  sources: ReportSource[];
}

export function SourceList({ sources }: SourceListProps) {
  if (!sources.length) return null;

  return (
    <section
      id="sources"
      aria-labelledby="sources-title"
      className="mt-16 pt-8 border-t border-border/60"
    >
      <h2
        id="sources-title"
        className="text-[1.2rem] mb-5 text-foreground/95"
        style={{
          fontFamily: "var(--font-display)",
          fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
          fontWeight: 400,
        }}
      >
        溯源
      </h2>
      <ol className="space-y-2.5">
        {sources.map((s) => (
          <li
            key={s.id}
            className="flex items-baseline gap-3 text-[12.5px] leading-relaxed"
          >
            <span
              className="tabular text-muted-foreground/70 w-12 shrink-0"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {s.id}
            </span>
            <div className="flex-1 min-w-0">
              <a
                href={s.url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-foreground/90 hover:text-primary inline-flex items-baseline gap-1 underline decoration-border underline-offset-4 hover:decoration-primary"
              >
                {s.title}
                <ExternalLink className="h-3 w-3 self-center" aria-hidden="true" />
              </a>
              <p className="text-muted-foreground/85 mt-0.5">{s.snippet}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
