import type { ReportSource, SourceTier } from "@/lib/api/reports";

// Authority tiers descend in visual weight: saturated teal → warm ochre → neutral gray.
export const TIER_META: Record<SourceTier, { color: string; desc: string }> = {
  A: { color: "var(--primary)", desc: "官方 / 权威来源" },
  B: { color: "var(--accent-warm)", desc: "可信二手媒体" },
  C: { color: "var(--muted-foreground)", desc: "用户评价 / 博客 / 未知" },
};

export const TIER_ORDER: SourceTier[] = ["A", "B", "C"];

// Ungraded sources (null) are shown as C, matching the PDF/Markdown exporters.
export function tierOf(s: ReportSource): SourceTier {
  return s.tier ?? "C";
}

// `decorative` hides the badge from assistive tech — use it where adjacent text
// already names the tier (e.g. the legend), to avoid the label being read twice.
export function TierBadge({ tier, decorative = false }: { tier: SourceTier; decorative?: boolean }) {
  const meta = TIER_META[tier];
  const a11y = decorative
    ? { "aria-hidden": true }
    : { role: "img", "aria-label": `来源可信档位 ${tier}，${meta.desc}` };
  return (
    <span
      {...a11y}
      title={`来源可信档位 ${tier} · ${meta.desc}`}
      className="inline-flex h-[15px] min-w-[15px] shrink-0 translate-y-px items-center justify-center rounded-[3px] px-1 text-[9.5px] font-medium leading-none tabular-nums"
      style={{
        fontFamily: "var(--font-mono)",
        color: meta.color,
        backgroundColor: `color-mix(in oklch, ${meta.color} 13%, transparent)`,
        border: `1px solid color-mix(in oklch, ${meta.color} 32%, transparent)`,
      }}
    >
      {tier}
    </span>
  );
}
