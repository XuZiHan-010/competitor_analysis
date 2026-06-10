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
      <ol className="space-y-3.5">
        {sources.map((s, index) => (
          <li
            key={`${s.id}-${index}`}
            id={s.id}
            className="grid grid-cols-[auto_1fr] gap-x-3 text-[12.5px] leading-relaxed scroll-mt-20"
          >
            <span
              className="tabular text-muted-foreground/60 tabular-nums"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {index + 1}.
            </span>
            <div className="min-w-0">
              <a
                href={s.url ?? undefined}
                target="_blank"
                rel="noreferrer noopener"
                className="text-foreground/90 hover:text-primary inline-flex items-baseline gap-1 underline decoration-border underline-offset-4 hover:decoration-primary"
              >
                {s.title}
                <ExternalLink className="h-3 w-3 self-center shrink-0" aria-hidden="true" />
              </a>
              <p
                className="text-[10.5px] text-muted-foreground/55 break-all mt-0.5"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {s.id}
              </p>
              {s.snippet && (
                <p className="text-muted-foreground/85 mt-1 break-words">{s.snippet}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
