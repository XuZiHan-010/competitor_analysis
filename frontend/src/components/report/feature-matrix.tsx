import type { FeatureRow, ReportSource } from "@/lib/api/reports";
import { CitationChips } from "./citation-chips";
import { cn } from "@/lib/utils";

const SUPPORT_GLYPH: Record<string, { label: string; tone: string }> = {
  supported: { label: "●", tone: "text-primary" },
  partial: { label: "◐", tone: "text-[var(--color-accent-warm)]" },
  unsupported: { label: "○", tone: "text-muted-foreground/60" },
  unknown: { label: "?", tone: "text-muted-foreground/40" },
};

interface FeatureMatrixProps {
  rows: FeatureRow[];
  competitors: string[];
  sources: ReportSource[];
}

export function FeatureMatrix({ rows, competitors, sources }: FeatureMatrixProps) {
  if (!rows.length) return null;

  return (
    <div className="overflow-x-auto -mx-2 px-2">
      <table className="w-full border-collapse text-[13.5px]">
        <thead>
          <tr
            className="border-b border-border/80 text-[11px] uppercase tracking-[0.15em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <th className="text-left font-normal py-2.5 pr-4 w-[200px]">功能</th>
            {competitors.map((c) => (
              <th key={c} className="text-left font-normal py-2.5 pr-4">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
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
                const glyph = SUPPORT_GLYPH[cell?.status ?? "unknown"];
                return (
                  <td key={c} className="py-3 pr-4">
                    <span
                      className={cn("inline-flex items-baseline gap-1.5", glyph.tone)}
                      title={cell?.status}
                    >
                      <span aria-hidden="true">{glyph.label}</span>
                      <span className="text-foreground/85 text-[12.5px]">
                        {cell?.note ?? "—"}
                      </span>
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
