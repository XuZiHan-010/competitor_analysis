import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type DataSourceStatus = "enabled" | "roadmap";

interface DataSourceCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  status: DataSourceStatus;
  statusLabel: string;
  /** Short note shown under the status pill, e.g. scope or trust boundary. */
  meta?: string;
}

/**
 * Read-only data-source row for the Settings page. Pure presentation — no
 * upload/connect actions. "roadmap" rows are dimmed to read as not-yet-built,
 * serving as the visual anchor for the RAG narrative (PRD §十一-ter).
 */
export function DataSourceCard({
  icon: Icon,
  title,
  description,
  status,
  statusLabel,
  meta,
}: DataSourceCardProps) {
  const roadmap = status === "roadmap";
  return (
    <div
      className={cn(
        "rounded-md border border-border/60 bg-card/40 px-5 py-4",
        roadmap && "opacity-60",
      )}
    >
      <div className="flex items-start gap-4">
        <span
          className={cn(
            "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded border",
            roadmap
              ? "border-border/60 text-muted-foreground/60"
              : "border-primary/30 bg-primary/8 text-primary",
          )}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <h3
              className="text-[1.05rem] leading-snug tracking-tight text-foreground"
              style={{ fontFamily: "var(--font-display)", fontWeight: 420 }}
            >
              {title}
            </h3>
            <span
              className={cn(
                "inline-flex shrink-0 items-center rounded border px-1.5 py-0.5",
                "text-[10px] uppercase tracking-[0.12em]",
                roadmap
                  ? "border-border/60 text-muted-foreground/70"
                  : "border-[oklch(0.62_0.17_145)]/30 bg-[oklch(0.62_0.17_145)]/8 text-[oklch(0.62_0.17_145)]",
              )}
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {statusLabel}
            </span>
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
          {meta && (
            <p
              className="mt-2 text-[11px] uppercase tracking-[0.1em] text-muted-foreground/55"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {meta}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
