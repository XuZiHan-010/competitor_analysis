"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface ChapterProps {
  index: number;
  title: string;
  kicker?: string;
  children: React.ReactNode;
  /** If provided, renders an edit button that calls this with the chapter index */
  onEdit?: (index: number) => void;
  edited?: boolean;
}

export function Chapter({ index, title, kicker, children, onEdit, edited }: ChapterProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <section
      className="mt-14 first:mt-0 scroll-mt-24"
      aria-labelledby={`ch-${index}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <p
            className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground mb-2"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            Ch. {String(index).padStart(2, "0")}
            {kicker ? ` · ${kicker}` : null}
          </p>
          <h2
            id={`ch-${index}`}
            className="text-[1.8rem] leading-[1.1] tracking-tight text-foreground"
            style={{
              fontFamily: "var(--font-display)",
              fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
              fontWeight: 400,
              textWrap: "balance",
            }}
          >
            {title}
          </h2>
        </div>

        {onEdit && (
          <div className="flex items-center gap-2 shrink-0 mt-1">
            {edited && (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded border border-[var(--color-accent-warm)]/40 text-[var(--color-accent-warm)] bg-[var(--color-accent-warm)]/8"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                已编辑
              </span>
            )}
            <button
              onClick={() => onEdit(index)}
              aria-label={`编辑章节 ${title}`}
              className={cn(
                "inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded border",
                "transition-all duration-150",
                hovered
                  ? "border-border text-foreground/70 bg-card"
                  : "border-transparent text-transparent",
                "focus-visible:border-border focus-visible:text-foreground/70 focus-visible:outline-none",
              )}
              style={{ fontFamily: "var(--font-mono)" }}
            >
              ✎ 编辑章节
            </button>
          </div>
        )}
      </div>
      {children}
    </section>
  );
}
