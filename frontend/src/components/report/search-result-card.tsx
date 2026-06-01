import Link from "next/link";
import { ArrowUpRight, FileText, Link2 } from "lucide-react";
import type { ReportSearchResultItem } from "@/lib/api/reports";
import { cn } from "@/lib/utils";

interface SearchResultCardProps {
  item: ReportSearchResultItem;
  /** Search term, highlighted within the snippet when present. */
  query?: string;
}

/**
 * Editorial index card for one historical report match. Pure presentation —
 * the whole card links to the report keyed by task_id (matching fetchReport).
 */
export function SearchResultCard({ item, query }: SearchResultCardProps) {
  return (
    <li className="group">
      <Link
        href={`/reports/${item.task_id}`}
        className={cn(
          "block rounded-md border border-border/60 bg-card/40 px-5 py-4",
          "transition-colors hover:bg-card/70 hover:border-border",
          "focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        )}
      >
        <div className="flex items-start justify-between gap-4">
          <h3
            className="text-[1.05rem] leading-snug tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-display)", fontWeight: 420, textWrap: "balance" }}
          >
            {item.title}
          </h3>
          <ArrowUpRight
            className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/50 transition-colors group-hover:text-[var(--color-accent-warm)]"
            aria-hidden="true"
          />
        </div>

        <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
          {highlight(item.snippet, query)}
        </p>

        <div
          className="mt-3.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[10px] uppercase tracking-[0.14em] text-muted-foreground/60"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          <span
            className={cn(
              "inline-flex items-center rounded border px-1.5 py-0.5",
              "border-border/60 text-muted-foreground/70",
            )}
          >
            {item.language === "zh" ? "中文" : "EN"}
          </span>
          <span className="inline-flex items-center gap-1 tabular">
            <FileText className="h-3 w-3" aria-hidden="true" />
            {item.claim_ids.length} claims
          </span>
          <span className="inline-flex items-center gap-1 tabular">
            <Link2 className="h-3 w-3" aria-hidden="true" />
            {item.source_ids.length} sources
          </span>
        </div>
      </Link>
    </li>
  );
}

/** Case-insensitively wrap query hits in <mark>. Plain text in/out — no HTML injection. */
function highlight(text: string, query?: string) {
  const term = query?.trim();
  if (!term) return text;
  const segments = text.split(new RegExp(`(${escapeRegExp(term)})`, "ig"));
  return segments.map((segment, i) =>
    segment.toLowerCase() === term.toLowerCase() ? (
      <mark key={i} className="rounded-sm bg-[var(--color-accent-warm)]/25 px-0.5 text-foreground">
        {segment}
      </mark>
    ) : (
      segment
    ),
  );
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
