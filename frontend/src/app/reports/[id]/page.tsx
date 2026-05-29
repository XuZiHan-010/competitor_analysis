"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, Download, FileDown, FileText } from "lucide-react";
import { toast } from "sonner";
import { PageContainer } from "@/components/layout/page-container";
import { Chapter } from "@/components/report/chapter";
import { ChapterEditor } from "@/components/report/chapter-editor";
import { CitationChips } from "@/components/report/citation-chips";
import { CitationPanel } from "@/components/report/citation-panel";
import { FeatureMatrix } from "@/components/report/feature-matrix";
import { MetricBadges } from "@/components/report/metric-badges";
import { PersonaCard } from "@/components/report/persona-card";
import { PositioningCard } from "@/components/report/positioning-card";
import { PricingTable } from "@/components/report/pricing-table";
import { QualityPanel } from "@/components/report/quality-panel";
import { SourceList } from "@/components/report/source-list";
import { SurveySection } from "@/components/report/survey-section";
import { SwotBlock } from "@/components/report/swot-block";
import {
  correctSection,
  exportReport,
  fetchReport,
  reviewClaim,
  type CorrectionType,
  type Report,
  type ReviewStatus,
} from "@/lib/api/reports";
import { cn } from "@/lib/utils";

interface EditState {
  chapterIndex: number;
  fieldPath: string;
  claimId: string;
  initialContent: string;
}

// Paths for editable intro fields in core chapters
const CHAPTER_PATHS: Record<number, string> = {
  1: "feature_tree.intro",
  2: "pricing.intro",
  3: "user_personas.intro",
  4: "swot.intro",
};

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const taskId = params.id;

  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [reviewMode, setReviewMode] = useState(false);
  const [editedChapters, setEditedChapters] = useState<Set<number>>(new Set());

  useEffect(() => {
    let mounted = true;
    fetchReport(taskId)
      .then((r) => {
        if (mounted) { setReport(r); setLoading(false); }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setError(err instanceof Error ? err.message : "报告加载失败");
          setLoading(false);
        }
      });
    return () => { mounted = false; };
  }, [taskId]);

  function handleEdit(chapterIndex: number) {
    if (!report) return;
    const sc = report.structured_content;
    const path = CHAPTER_PATHS[chapterIndex];
    if (!path) return;

    const contentMap: Record<string, string> = {
      "feature_tree.intro": sc.feature_tree.intro,
      "pricing.intro": sc.pricing.intro,
      "user_personas.intro": sc.user_personas.intro,
      "swot.intro": sc.swot.intro,
    };
    const claim = report.claims.find((c) => c.claim_path === path);
    setEditState({
      chapterIndex,
      fieldPath: path,
      claimId: claim?.id ?? "",
      initialContent: contentMap[path] ?? "",
    });
  }

  async function handleSaveEdit(payload: {
    claimId: string;
    fieldPath: string;
    newValue: string;
    correctionType: CorrectionType;
  }) {
    if (!editState) return;
    try {
      const updated = await correctSection(taskId, {
        claim_id: payload.claimId,
        field_path: payload.fieldPath,
        new_value: payload.newValue,
        correction_type: payload.correctionType,
      });
      setReport(updated);
      setEditedChapters((prev) => new Set([...prev, editState.chapterIndex]));
      setEditState(null);
      toast.success("章节已保存");
    } catch {
      toast.error("保存失败，请重试");
    }
  }

  async function handleReviewClaim(claimId: string, status: ReviewStatus) {
    try {
      const updated = await reviewClaim(taskId, claimId, status);
      setReport(updated);
    } catch {
      toast.error("复核状态更新失败");
    }
  }

  async function handleExport(format: "pdf" | "pptx" | "markdown") {
    try {
      const blob = await exportReport(taskId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${taskId.slice(0, 8)}.${format === "markdown" ? "md" : format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error(`${format.toUpperCase()} 导出失败`);
    }
  }

  if (loading) return <ReportSkeleton />;
  if (error || !report) return <ReportError message={error ?? "未知错误"} />;

  const { structured_content: sc, sources, claims, metrics } = report;
  const crossMatrix = sc.cross_analysis.feature_matrix;
  const positioningMap = sc.cross_analysis.positioning_map;

  function editorFor(idx: number) {
    if (editState?.chapterIndex !== idx) return null;
    return (
      <ChapterEditor
        initialContent={editState.initialContent}
        fieldPath={editState.fieldPath}
        claimId={editState.claimId}
        onSave={handleSaveEdit}
        onCancel={() => setEditState(null)}
      />
    );
  }

  return (
    <>
      <PageContainer width="wide" className="max-w-[1024px]">
        <div className="flex gap-8 items-start">
          {/* ── Main content ── */}
          <div className="flex-1 min-w-0">
            {/* Masthead */}
            <header className="mb-12 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_both]">
              <p
                className="mb-3 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                报告 · {new Date(report.created_at).toLocaleDateString("zh-CN")}
              </p>
              <h1
                className="text-[2.1rem] leading-[1.02] sm:text-[clamp(2.5rem,5vw,3.4rem)] tracking-tight text-foreground mb-4"
                style={{
                  fontFamily: "var(--font-display)",
                  fontVariationSettings: '"opsz" 144, "SOFT" -50, "WONK" 1',
                  fontWeight: 380,
                  textWrap: "balance",
                }}
              >
                {sc.title}
              </h1>
              {sc.subtitle && (
                <p
                  className="text-[15px] text-muted-foreground italic"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {sc.subtitle}
                </p>
              )}

              <div className="mt-5">
                <MetricBadges metrics={metrics} />
              </div>

              <div className="mt-5 flex flex-wrap items-center gap-2">
                {(
                  [
                    { format: "pdf", icon: <Download className="h-3.5 w-3.5" />, label: "PDF" },
                    { format: "pptx", icon: <FileText className="h-3.5 w-3.5" />, label: "PPTX" },
                    { format: "markdown", icon: <FileDown className="h-3.5 w-3.5" />, label: "MD" },
                  ] as const
                ).map(({ format, icon, label }) => (
                  <button
                    key={format}
                    onClick={() => handleExport(format)}
                    className="inline-flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded border border-border/70 text-foreground/70 hover:text-foreground hover:border-border transition-colors"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {icon} {label}
                  </button>
                ))}
              </div>

              <div className="rule-fade mt-8" aria-hidden="true" />
            </header>

            {/* Ch 1 — Feature tree */}
            <Chapter
              index={1} title="功能树"
              onEdit={handleEdit} edited={editedChapters.has(1)}
            >
              {sc.feature_tree.intro && (
                <p className="drop-cap text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
                  {sc.feature_tree.intro}
                </p>
              )}
              {editorFor(1)}
              <FeatureMatrix
                rows={sc.feature_tree.rows}
                competitors={sc.competitors}
                sources={sources}
              />
            </Chapter>

            {/* Ch 2 — Pricing */}
            <Chapter
              index={2} title="定价模型"
              onEdit={handleEdit} edited={editedChapters.has(2)}
            >
              {sc.pricing.intro && (
                <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
                  {sc.pricing.intro}
                </p>
              )}
              {editorFor(2)}
              <PricingTable tiers={sc.pricing.tiers} sources={sources} />
            </Chapter>

            {/* Ch 3 — User personas */}
            <Chapter
              index={3} title="用户画像"
              onEdit={handleEdit} edited={editedChapters.has(3)}
            >
              {sc.user_personas.intro && (
                <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
                  {sc.user_personas.intro}
                </p>
              )}
              {editorFor(3)}
              <div className="grid gap-5 md:grid-cols-3">
                {sc.user_personas.personas.map((p, i) => (
                  <PersonaCard key={i} persona={p} sources={sources} />
                ))}
              </div>
            </Chapter>

            {/* Ch 4 — SWOT */}
            <Chapter
              index={4} title="SWOT"
              onEdit={handleEdit} edited={editedChapters.has(4)}
            >
              {sc.swot.intro && (
                <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
                  {sc.swot.intro}
                </p>
              )}
              {editorFor(4)}
              <div className="space-y-6">
                {sc.swot.blocks.map((b, i) => (
                  <SwotBlock key={i} block={b} sources={sources} />
                ))}
              </div>
            </Chapter>

            {/* Extension chapters */}
            {sc.extensions.map((ext, idx) => {
              const chIndex = 5 + idx;
              return (
                <Chapter
                  key={ext.dimension_id}
                  index={chIndex}
                  title={ext.title}
                  kicker="AI 建议扩展维度"
                >
                  {ext.intent && (
                    <p className="text-[14.5px] italic text-muted-foreground/90 mb-4">
                      意图：{ext.intent}
                    </p>
                  )}
                  {ext.summary && (
                    <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
                      {ext.summary}
                    </p>
                  )}
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
                          {b.points.map((pt, pi) => (
                            <li key={pi} className="flex gap-2">
                              <span
                                aria-hidden="true"
                                className="text-muted-foreground/70 mt-1 shrink-0"
                              >
                                —
                              </span>
                              <span>{pt}</span>
                            </li>
                          ))}
                        </ul>
                        <CitationChips ids={b.source_ids} sources={sources} />
                      </article>
                    ))}
                  </div>
                </Chapter>
              );
            })}

            {/* Cross-competitor analysis */}
            {(crossMatrix ?? positioningMap ?? sc.cross_analysis.differentiation_summary) && (
              <Chapter
                index={5 + sc.extensions.length}
                title="跨竞品总结"
              >
                {sc.cross_analysis.differentiation_summary && (
                  <p className="text-[15.5px] leading-[1.85] text-foreground/90 mb-6">
                    {sc.cross_analysis.differentiation_summary}
                  </p>
                )}
                <div
                  className={cn(
                    "grid gap-6",
                    crossMatrix && positioningMap ? "md:grid-cols-[1fr_320px]" : "",
                  )}
                >
                  {crossMatrix && (
                    <FeatureMatrix
                      rows={crossMatrix.rows}
                      competitors={crossMatrix.competitors}
                      sources={sources}
                    />
                  )}
                  {positioningMap && (
                    <PositioningCard
                      xAxis={positioningMap.x_axis}
                      yAxis={positioningMap.y_axis}
                      points={positioningMap.competitors}
                    />
                  )}
                </div>
              </Chapter>
            )}

            {/* Survey — user voices */}
            <SurveySection results={sc.survey} />

            <SourceList sources={sources} />
          </div>

          {/* ── Sidebar ── */}
          <QualityPanel
            metrics={metrics}
            claims={claims}
            reviewMode={reviewMode}
            onToggleReviewMode={() => setReviewMode((v) => !v)}
            onReviewClaim={handleReviewClaim}
          />
        </div>
      </PageContainer>

      {/* Citation fly-over panel (portal-like, rendered outside main scroll) */}
      <CitationPanel sources={sources} />
    </>
  );
}

// ─── Loading / error states ───────────────────────────────────────────────────

function ReportSkeleton() {
  return (
    <PageContainer width="wide" className="max-w-[1024px]">
      <div className="flex gap-8">
        <div className="flex-1 min-w-0 space-y-6">
          <div className="space-y-3">
            <div className="h-3 w-24 rounded bg-border/60 animate-pulse" />
            <div className="h-9 w-3/4 rounded bg-border/60 animate-pulse" />
            <div className="h-5 w-1/2 rounded bg-border/50 animate-pulse" />
          </div>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-3 pt-8">
              <div className="h-3 w-16 rounded bg-border/50 animate-pulse" />
              <div className="h-7 w-40 rounded bg-border/60 animate-pulse" />
              <div className="h-[100px] w-full rounded bg-border/40 animate-pulse" />
            </div>
          ))}
        </div>
        <div className="hidden lg:block w-[280px] shrink-0">
          <div className="h-[300px] rounded-md border border-border/60 bg-card/40 animate-pulse" />
        </div>
      </div>
    </PageContainer>
  );
}

function ReportError({ message }: { message: string }) {
  return (
    <PageContainer width="wide">
      <div className="flex items-center gap-3 rounded-md border border-destructive/30 bg-destructive/8 px-5 py-4">
        <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
        <p className="text-sm text-destructive">{message}</p>
      </div>
    </PageContainer>
  );
}
