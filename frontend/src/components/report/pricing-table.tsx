import type { PricingTier, ReportSource } from "@/lib/api/reports";
import { CitationChips } from "./citation-chips";

interface PricingTableProps {
  tiers: PricingTier[];
  sources: ReportSource[];
}

export function PricingTable({ tiers, sources }: PricingTableProps) {
  if (!tiers.length) return null;

  return (
    <div className="overflow-x-auto -mx-2 px-2">
      <table className="w-full border-collapse text-[13.5px]">
        <thead>
          <tr
            className="border-b border-border/80 text-[11px] uppercase tracking-[0.15em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <th className="text-left font-normal py-2.5 pr-4 w-[110px]">竞品</th>
            <th className="text-left font-normal py-2.5 pr-4">档位</th>
            <th className="text-right font-normal py-2.5 pr-4 w-[110px]">价格</th>
            <th className="text-left font-normal py-2.5">亮点</th>
          </tr>
        </thead>
        <tbody>
          {tiers.map((t, idx) => (
            <tr key={idx} className="border-b border-border/40 align-baseline">
              <td className="py-2.5 pr-4 text-foreground/95">{t.competitor}</td>
              <td className="py-2.5 pr-4 text-foreground/90">{t.tier}</td>
              <td
                className="tabular py-2.5 pr-4 text-right text-foreground/95"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {t.price}
              </td>
              <td className="py-2.5 text-muted-foreground">
                {t.highlights.join(" · ")}
                <CitationChips ids={t.source_ids} sources={sources} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
