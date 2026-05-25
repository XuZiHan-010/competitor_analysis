"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageContainer } from "@/components/layout/page-container";
import { useScopingStore } from "@/stores/scoping-store";
import { simulateAIThinking } from "@/lib/mocks/delay";
import { buildEmptyDraftContract } from "@/lib/mocks/scope-contract";
import { CompetitorChips } from "@/components/scoping/competitor-chips";
import { DimensionList } from "@/components/scoping/dimension-list";
import { AddDimensionDialog } from "@/components/scoping/add-dimension-dialog";
import { ReguideInput } from "@/components/scoping/reguide-input";
import { cn } from "@/lib/utils";

export default function ScopingPage() {
  const {
    userBrief,
    draftContract,
    isGenerating,
    setDraftContract,
    setIsGenerating,
  } = useScopingStore();

  const [confirming, setConfirming] = useState(false);

  // Real path (PRD §十一-quater 11Q.7): ScopingAgent backend not yet wired up,
  // so we render an empty skeleton (4 core + 0 extensions + 0 competitors)
  // built from whatever the user typed. NEVER fall back to a domain-bound mock
  // — that would mean "type AI IDE, see skincare outline" on demo day.
  useEffect(() => {
    if (draftContract) return;

    setIsGenerating(true);
    simulateAIThinking(900).then(() => {
      setDraftContract(buildEmptyDraftContract(userBrief));
      setIsGenerating(false);
    });
  }, [draftContract, userBrief, setDraftContract, setIsGenerating]);

  async function handleConfirm() {
    if (!draftContract) return;
    setConfirming(true);
    await simulateAIThinking(700);
    setDraftContract({
      ...draftContract,
      frozen_at: new Date().toISOString(),
    });
    toast.success("任务已创建", {
      description: "Stage 2 接入 DAG 页后会跳到运行页",
    });
    setConfirming(false);
    // Stage 2 will route to /tasks/{id}. For now stay put.
  }

  const enabledCount =
    draftContract?.dimensions.filter((d) => d.enabled).length ?? 0;
  const totalCount = draftContract?.dimensions.length ?? 0;

  return (
    <PageContainer width="narrow" className="pb-32">
      {/* Editorial header strip */}
      <div className="flex items-baseline gap-3 mb-8 animate-[fade-in_0.4s_ease-out]">
        <Link
          href="/tasks/new"
          className="inline-flex items-center gap-1 text-xs uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground transition-colors"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          <ArrowLeft className="h-3 w-3" />
          重写需求
        </Link>
        <span className="h-px flex-1 bg-border" />
        <span
          className="tabular text-xs uppercase tracking-[0.22em] text-primary"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          Scoping / 立项中
        </span>
      </div>

      {/* sr-only h1 for screen reader semantics */}
      <h1 className="sr-only">确定分析维度</h1>

      {/* Loading state */}
      {isGenerating && !draftContract && (
        <div className="flex flex-col items-center justify-center py-24 gap-4 animate-[fade-in_0.3s_ease-out]">
          <div className="relative">
            <Sparkles
              className="h-8 w-8 text-primary animate-[thinking-pulse_2s_ease-in-out_infinite]"
              strokeWidth={1.5}
            />
          </div>
          <p
            className="text-sm uppercase tracking-[0.22em] text-muted-foreground animate-[thinking-pulse_2s_ease-in-out_infinite]"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            Scoping Agent 正在分析需求
          </p>
        </div>
      )}

      {draftContract && (
        <>
          {/* Intro paragraph + Subjects band */}
          <section className="mb-10 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.05s_both]">
            <p className="text-base text-muted-foreground leading-relaxed max-w-[52ch] mb-6">
              AI 已根据需求拟了一份大纲：
              <span className="tabular font-medium text-foreground mx-1">
                4&nbsp;项核心
              </span>
              维度（不可删除）加
              <span className="tabular font-medium text-foreground mx-1">
                {Math.max(0, totalCount - 4)}&nbsp;项扩展
              </span>
              维度。你可以编辑标题、改意图、增删扩展项、调整顺序。
            </p>
            <CompetitorChips />
          </section>

          {/* Outline section */}
          <section className="mb-10 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.15s_both]">
            <div className="flex items-baseline justify-between mb-4">
              <h2
                className="text-xl text-foreground"
                style={{
                  fontVariationSettings: '"opsz" 36',
                  fontWeight: 500,
                }}
              >
                本次分析大纲
              </h2>
              <span
                className="tabular text-xs text-muted-foreground"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {enabledCount} / {totalCount} 启用
              </span>
            </div>

            <p className="text-xs text-muted-foreground mb-4 italic">
              拖拽 ⋮ 调整顺序 · 点标题或意图直接编辑 · 取消勾选 = 本次不输出
            </p>

            <div
              className={cn(
                "transition-opacity",
                isGenerating && "opacity-50 pointer-events-none",
              )}
            >
              <DimensionList dimensions={draftContract.dimensions} />
            </div>

            <div className="mt-3">
              <AddDimensionDialog />
            </div>

            <ReguideInput />
          </section>
        </>
      )}

      {/* Sticky action bar at bottom */}
      {draftContract && (
        <div
          className={cn(
            "fixed bottom-0 left-0 right-0 z-30",
            "border-t border-border bg-background/95 backdrop-blur",
            "supports-[backdrop-filter]:bg-background/85",
          )}
        >
          <div className="mx-auto max-w-[720px] px-4 py-3 sm:px-8 sm:py-4 flex justify-end">
            <Button
              onClick={handleConfirm}
              disabled={isGenerating || confirming || enabledCount === 0}
              size="lg"
              className={cn(
                "group h-11 w-full sm:w-auto px-6 font-medium",
                "bg-primary text-primary-foreground hover:bg-primary/90",
                "shadow-[0_4px_14px_-4px_oklch(0.38_0.065_220_/_0.4)]",
              )}
            >
              {confirming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  确认 · 开始分析
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </PageContainer>
  );
}
