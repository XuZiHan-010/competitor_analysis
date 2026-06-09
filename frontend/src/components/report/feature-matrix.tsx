import type { FeatureCell, FeatureRow, ReportSource } from "@/lib/api/reports";
import { CitationChips } from "./citation-chips";
import { cn } from "@/lib/utils";

type FeatureStatus = FeatureCell["status"];

// `unknown` renders as a quiet em-dash (not "?") so sparse cross-competitor
// matrices read as "no data" rather than looking broken.
const SUPPORT_GLYPH: Record<FeatureStatus, { label: string; tone: string }> = {
  supported: { label: "●", tone: "text-primary" },
  partial: { label: "◐", tone: "text-[var(--color-accent-warm)]" },
  unsupported: { label: "○", tone: "text-muted-foreground/60" },
  unknown: { label: "—", tone: "text-muted-foreground/40" },
};

function normalizeFeatureStatus(status: unknown): FeatureStatus {
  return status === "supported" ||
    status === "partial" ||
    status === "unsupported" ||
    status === "unknown"
    ? status
    : "unknown";
}

interface FeatureMatrixProps {
  rows: FeatureRow[];
  competitors: string[];
  sources: ReportSource[];
}

export function FeatureMatrix({ rows, competitors, sources }: FeatureMatrixProps) {
  // Drop rows where no competitor has any data — an all-"unknown" row adds noise.
  const visibleRows = rows.filter((row) =>
    row.cells.some((cell) => normalizeFeatureStatus(cell.status) !== "unknown"),
  );
  if (!visibleRows.length) return null;

  return (
    <div className="overflow-x-auto -mx-2 px-2">
      <table className="w-full min-w-[680px] border-collapse text-[13.5px]">
        <thead>
          <tr
            className="border-b border-border/80 text-[11px] uppercase tracking-[0.15em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <th className="text-left font-normal py-2.5 pr-4 w-[200px]">功能</th>
            {competitors.map((c) => (
              <th key={c} className="text-left font-normal py-2.5 pr-4 min-w-[140px]">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, idx) => (
            <tr key={idx} className="border-b border-border/40 align-top">
              <td className="py-3 pr-4">
                <p className="text-foreground/95">{row.feature}</p>
                {row.description && (
                  <p className="text-[11.5px] text-muted-foreground/85 mt-0.5 leading-snug">
                    {row.description}
                  </p>
                )}
                <CitationChips ids={row.source_ids} sources={sources} />
              </td>
              {competitors.map((c) => {
                const cell = row.cells.find((cc) => cc.competitor === c);
                const status = normalizeFeatureStatus(cell?.status);
                const glyph = SUPPORT_GLYPH[status];
                return (
                  <td key={c} className="py-3 pr-4 align-top min-w-[140px]">
                    <span className={cn("inline-flex items-baseline gap-1.5", glyph.tone)}>
                      <span aria-hidden="true">{glyph.label}</span>
                      {cell?.note && (
                        <span className="text-foreground/85 text-[12.5px] break-words">
                          {cell.note}
                        </span>
                      )}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
