"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { Download, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { PageContainer } from "@/components/layout/page-container";
import { DemoWatermark } from "@/components/demo/demo-watermark";
import {
  fallbackDemoReplayBundle,
  fetchDemoReplayBundle,
} from "@/lib/api/demo";
import type {
  DemoFeatureRow,
  DemoPersona,
  DemoSource,
  DemoSwotBlock,
} from "@/lib/mocks/demo/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SUPPORT_GLYPH: Record<string, { label: string; tone: string }> = {
  supported: { label: "●", tone: "text-primary" },
  partial: { label: "◐", tone: "text-[var(--color-accent-warm)]" },
  unsupported: { label: "○", tone: "text-muted-foreground/60" },
  unknown: { label: "?", tone: "text-muted-foreground/40" },
};

const DemoSourcesContext = createContext<DemoSource[]>([]);

export default function DemoReportPage() {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [demoReplay, setDemoReplay] = useState(() => fallbackDemoReplayBundle());
  const demoReport = demoReplay.report;
  const demoSources = demoReplay.sources;

  useEffect(() => {
    titleRef.current?.focus();
    let mounted = true;
    fetchDemoReplayBundle()
      .then((bundle) => {
        if (!mounted) return;
        setDemoReplay(bundle);
      })
      .catch(() => {
        // Keep the pre-recorded local fixture available without backend.
      });
    return () => {
      mounted = false;
    };
  }, []);

  function handleExport(kind: "pdf") {
    toast("演示样例", {
      description: `${kind.toUpperCase()} 导出在真实任务中可用 · 当前路径为预录回放`,
    });
  }

  return (
    <DemoSourcesContext.Provider value={demoSources}>
      <DemoWatermark step={3} />

      <PageContainer width="wide" className="max-w-[1024px]">
        {/* Masthead */}
        <header className="mb-12 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_both]">
          <p
            className="mb-3 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            DEMO · Ch. 03 — 报告交付物
          </p>
          <h1
            ref={titleRef}
            tabIndex={-1}
            className={cn(
              "text-[2.1rem] leading-[1.02] sm:text-[clamp(2.5rem,5vw,3.4rem)]",
              "tracking-tight text-foreground mb-4",
              "outline-none focus-visible:outline-none",
            )}
            style={{
              fontVariationSettings: '"opsz" 144, "SOFT" -50, "WONK" 1',
              fontWeight: 380,
              textWrap: "balance",
            }}
          >
            {demoReport.title}
          </h1>
          <p
            className="text-[15px] text-muted-foreground italic"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {demoReport.subtitle}
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport("pdf")}
              className="gap-2"
            >
              <Download className="h-3.5 w-3.5" /> PDF
            </Button>
            <span
              className="tabular text-[11px] text-muted-foreground/80 ml-auto"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {new Date(demoReport.generated_at).toLocaleString("zh-CN")}
            </span>
          </div>

          <div className="rule-fade mt-8" aria-hidden="true" />
        </header>

        {/* Chapter 1 — Feature tree */}
        <Chapter index={1} title="功能树">
          <p className="drop-cap text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
            {demoReport.feature_tree.intro}
          </p>
          <FeatureMatrix
            rows={demoReport.feature_tree.rows}
            competitors={demoReport.competitors}
          />
        </Chapter>

        {/* Chapter 2 — Pricing */}
        <Chapter index={2} title="定价模型">
          <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
            {demoReport.pricing.intro}
          </p>
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
                {demoReport.pricing.tiers.map((t, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-border/40 align-baseline"
                  >
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
                      <CitationChips ids={t.source_ids} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Chapter>

        {/* Chapter 3 — User personas */}
        <Chapter index={3} title="用户画像">
          <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
            {demoReport.user_personas.intro}
          </p>
          <div className="grid gap-5 md:grid-cols-3">
            {demoReport.user_personas.personas.map((p, idx) => (
              <PersonaCard key={idx} persona={p} />
            ))}
          </div>
        </Chapter>

        {/* Chapter 4 — SWOT */}
        <Chapter index={4} title="SWOT">
          <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
            {demoReport.swot.intro}
          </p>
          <div className="space-y-6">
            {demoReport.swot.blocks.map((b, idx) => (
              <SwotBlock key={idx} block={b} />
            ))}
          </div>
        </Chapter>

        {/* Chapters 5+ — Extensions */}
        {demoReport.extensions.map((ext, idx) => (
          <Chapter
            key={ext.dimension_id}
            index={5 + idx}
            title={ext.title}
            kicker="AI 建议扩展维度"
          >
            <p className="text-[14.5px] italic text-muted-foreground/90 mb-4">
              意图：{ext.intent}
            </p>
            <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
              {ext.summary}
            </p>
            <div className="grid gap-4 md:grid-cols-3">
              {ext.bullets.map((b, bi) => (
                <article
                  key={bi}
                  className="rounded-md border border-border/60 bg-card/60 px-4 py-3.5"
                >
                  <p
                    className="text-[13px] mb-2 text-foreground/95"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {b.competitor}
                  </p>
                  <ul className="space-y-1.5 text-[12.5px] text-foreground/85 leading-relaxed">
                    {b.points.map((p, pi) => (
                      <li key={pi} className="flex gap-2">
                        <span
                          aria-hidden="true"
                          className="text-muted-foreground/70 mt-1 shrink-0"
                        >
                          —
                        </span>
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                  <CitationChips ids={b.source_ids} />
                </article>
              ))}
            </div>
          </Chapter>
        ))}

        {/* Cross competitor analysis */}
        <Chapter index={5 + demoReport.extensions.length} title="跨竞品总结">
          <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
            {demoReport.cross_analysis.differentiation_summary}
          </p>
          <div className="grid gap-6 md:grid-cols-[1fr_320px]">
            <FeatureMatrix
              rows={demoReport.cross_analysis.feature_matrix}
              competitors={demoReport.competitors}
            />
            <PositioningCard
              xAxis={demoReport.cross_analysis.positioning_map.x_axis}
              yAxis={demoReport.cross_analysis.positioning_map.y_axis}
              points={demoReport.cross_analysis.positioning_map.competitors}
            />
          </div>
        </Chapter>

        {/* Sources */}
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
            {demoSources.map((s) => (
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
      </PageContainer>
    </DemoSourcesContext.Provider>
  );
}

interface ChapterProps {
  index: number;
  title: string;
  kicker?: string;
  children: React.ReactNode;
}

function Chapter({ index, title, kicker, children }: ChapterProps) {
  return (
    <section className="mt-14 first:mt-0 scroll-mt-24" aria-labelledby={`ch-${index}`}>
      <p
        className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground mb-2"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        Ch. {String(index).padStart(2, "0")}
        {kicker ? ` · ${kicker}` : null}
      </p>
      <h2
        id={`ch-${index}`}
        className="text-[1.8rem] leading-[1.1] tracking-tight text-foreground mb-5"
        style={{
          fontFamily: "var(--font-display)",
          fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
          fontWeight: 400,
          textWrap: "balance",
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function FeatureMatrix({
  rows,
  competitors,
}: {
  rows: DemoFeatureRow[];
  competitors: string[];
}) {
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
                <p className="text-[11.5px] text-muted-foreground/85 mt-0.5 leading-snug">
                  {row.description}
                </p>
                <CitationChips ids={row.source_ids} />
              </td>
              {competitors.map((c) => {
                const cell = row.cells.find((cc) => cc.competitor === c);
                if (!cell) return <td key={c} />;
                const glyph = SUPPORT_GLYPH[cell.status];
                return (
                  <td key={c} className="py-3 pr-4">
                    <span
                      className={cn(
                        "inline-flex items-baseline gap-1.5",
                        glyph.tone,
                      )}
                      title={cell.status}
                    >
                      <span aria-hidden="true">{glyph.label}</span>
                      <span className="text-foreground/85 text-[12.5px]">
                        {cell.note ?? "—"}
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

function PersonaCard({ persona }: { persona: DemoPersona }) {
  return (
    <article className="rounded-md border border-border/60 bg-card/60 p-5">
      <p
        className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {persona.competitor} · {persona.size}
      </p>
      <p
        className="text-[1.05rem] my-2 text-foreground/95 leading-snug"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {persona.label}
      </p>

      <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground mt-3 mb-1">
        需求
      </p>
      <ul className="text-[12.5px] text-foreground/90 leading-relaxed space-y-0.5 mb-3">
        {persona.needs.map((n, i) => (
          <li key={i}>· {n}</li>
        ))}
      </ul>

      <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground mb-1">
        痛点
      </p>
      <ul className="text-[12.5px] text-foreground/90 leading-relaxed space-y-0.5 mb-3">
        {persona.pain_points.map((n, i) => (
          <li key={i}>· {n}</li>
        ))}
      </ul>

      <blockquote
        className="border-l-2 border-[var(--color-accent-warm)] pl-3 mt-3 text-[12px] italic text-foreground/80 leading-relaxed"
        style={{ fontFamily: "var(--font-display)" }}
      >
        “{persona.evidence}”
      </blockquote>
      <CitationChips ids={persona.source_ids} />
    </article>
  );
}

function SwotBlock({ block }: { block: DemoSwotBlock }) {
  const quads: { key: keyof DemoSwotBlock; label: string }[] = [
    { key: "strengths", label: "Strengths" },
    { key: "weaknesses", label: "Weaknesses" },
    { key: "opportunities", label: "Opportunities" },
    { key: "threats", label: "Threats" },
  ];

  return (
    <article className="rounded-md border border-border/60 bg-card/60 p-5">
      <p
        className="text-[1.05rem] mb-4 text-foreground/95"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {block.competitor}
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {quads.map((q) => {
          const items = block[q.key] as { text: string; source_ids: string[] }[];
          return (
            <div key={q.key}>
              <p
                className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-2"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {q.label}
              </p>
              <ul className="space-y-1.5 text-[12.5px] text-foreground/90 leading-relaxed">
                {items.map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span aria-hidden="true" className="text-muted-foreground/70 mt-1 shrink-0">
                      —
                    </span>
                    <span>
                      {item.text}
                      <CitationChips ids={item.source_ids} />
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function PositioningCard({
  xAxis,
  yAxis,
  points,
}: {
  xAxis: string;
  yAxis: string;
  points: { id: string; x: number; y: number; label: string }[];
}) {
  return (
    <aside
      aria-label="竞品定位图"
      className="rounded-md border border-border/60 bg-card/60 p-4"
    >
      <p
        className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-3"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        定位图
      </p>
      <div className="relative w-full aspect-square border border-border/60 bg-background/50">
        {/* Axis lines */}
        <span
          aria-hidden="true"
          className="absolute left-0 right-0 top-1/2 h-px bg-border/60"
        />
        <span
          aria-hidden="true"
          className="absolute top-0 bottom-0 left-1/2 w-px bg-border/60"
        />
        {points.map((p) => (
          <span
            key={p.id}
            className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center"
            style={{ left: `${p.x}%`, top: `${100 - p.y}%` }}
          >
            <span className="block h-2 w-2 rounded-full bg-[var(--color-accent-warm)]" />
            <span className="text-[10.5px] mt-1 text-foreground/90 whitespace-nowrap">
              {p.label}
            </span>
          </span>
        ))}
      </div>
      <p className="text-[10.5px] text-muted-foreground mt-2 leading-snug">
        x · {xAxis}
        <br />
        y · {yAxis}
      </p>
    </aside>
  );
}

function CitationChips({ ids }: { ids: string[] }) {
  const sources = useContext(DemoSourcesContext);
  if (!ids?.length) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-baseline">
      {ids.map((id) => {
        const src = sources.find((source) => source.id === id);
        if (!src) return null;
        return (
          <a
            key={id}
            href={`#sources`}
            title={src.title}
            className={cn(
              "tabular inline-flex items-center rounded-sm border border-border/70 bg-background/80 px-1",
              "text-[10px] uppercase tracking-[0.05em] text-muted-foreground/80",
              "hover:text-foreground hover:border-border",
              "no-underline",
            )}
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {id.replace("src_", "")}
          </a>
        );
      })}
    </span>
  );
}
