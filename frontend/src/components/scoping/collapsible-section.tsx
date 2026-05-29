"use client";

import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Generic collapsible card used to tame the scoping page's long sections.
 * Body height animates via the grid-rows 0fr→1fr technique (no height
 * measuring); the global prefers-reduced-motion reset neutralizes the
 * transition while keeping toggling functional.
 */
export function CollapsibleSection({
  title,
  badge,
  defaultOpen = true,
  accent = false,
  children,
}: {
  title: string;
  /** Optional pill shown next to the title (e.g. a count). */
  badge?: ReactNode;
  defaultOpen?: boolean;
  /** Tint the border to mark an opt-in / secondary section. */
  accent?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = useId();

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border bg-card/40",
        accent ? "border-primary/30" : "border-border/60",
      )}
    >
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex w-full items-center justify-between gap-3 px-5 py-4 text-left",
          "transition-colors hover:bg-card/60",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        )}
      >
        <span className="flex items-center gap-2.5">
          <span
            className="text-[1.05rem] text-foreground/95"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {title}
          </span>
          {badge}
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
            open && "rotate-180",
          )}
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
          <div className="border-t border-border/60 px-5 py-4">{children}</div>
        </div>
      </div>
    </div>
  );
}
