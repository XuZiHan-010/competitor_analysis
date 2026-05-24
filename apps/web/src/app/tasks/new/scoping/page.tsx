"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Loader2, RefreshCcw, Sparkles } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageContainer } from "@/components/layout/page-container";
import { useScopingStore } from "@/stores/scoping-store";
import { jitteredThinking, simulateAIThinking } from "@/lib/mocks/delay";
import {
  buildSkincareMockContract,
  extractCompetitorsFromBrief,
} from "@/lib/mocks/scope-contract";
import { CompetitorChips } from "@/components/scoping/competitor-chips";
import { DimensionList } from "@/components/scoping/dimension-list";
import { AddDimensionDialog } from "@/components/scoping/add-dimension-dialog";
import { cn } from "@/lib/utils";

export default function ScopingPage() {
  const {
    userBrief,
    manualCompetitors,
    draftContract,
    isGenerating,
    setDraftContract,
    setIsGenerating,
  } = useScopingStore();

  const [confirming, setConfirming] = useState(false);

  // Bootstrap: if the user landed here directly (or refreshed), fall back to
  // the mock skincare brief so the page is always demonstrable.
  useEffect(() => {
    if (draftContract) return;

    const briefForMock =
      userBrief ||
      "分析 SK-II、资生堂、雅诗兰黛 三个高端护肤品牌在中国电商的会员体系和 KOL 策略上的差异。";
    const extracted = extractCompetitorsFromBrief(briefForMock);
    const competitors = Array.from(
      new Set([...extracted, ...manualCompetitors]),
    );

    setIsGenerating(true);
    simulateAIThinking(1800).then(() => {
      setDraftContract(buildSkincareMockContract(briefForMock, competitors));
      setIsGenerating(false);
    });
  }, [
    draftContract,
    userBrief,
    manualCompetitors,
    setDraftContract,
    setIsGenerating,
  ]);

  async function handleRegenerate() {
    setIsGenerating(true);
    await jitteredThinking(1800, 500);
    if (!draftContract) {
      setIsGenerating(false);
      return;
    }
    // For the demo, "regenerate" just rebuilds from current brief +
    // current competitors. In Stage 3 this would call the real API
    // with the current edits as steering context.
    const fresh = buildSkincareMockContract(
      draftContract.user_brief,
      draftContract.competitors,
    );
    setDraftContract(fresh);
    setIsGenerating(false);
    toast.success("已重新生成大纲", {
      description: "基于当前需求与编辑过的章节",
    });
  }

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

      {/* Display heading */}
      <header className="mb-10 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.05s_both]">
        <h1
          className="text-[1.5rem] leading-[1.1] sm:text-[clamp(2rem,4vw,3rem)] sm:leading-[1.05] tracking-tight text-foreground mb-4"
          style={{
            fontVariationSettings: '"opsz" 144, "SOFT" 0',
            fontWeight: 400,
          }}
        >
          确定{" "}
          <em
            className="not-italic text-primary"
            style={{ fontVariationSettings: '"opsz" 144, "SOFT" 100' }}
          >
            分析维度
          </em>
        </h1>
        <p className="text-base text-muted-foreground leading-relaxed max-w-[48ch]">
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
      </header>

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
          {/* Subjects band */}
          <section className="mb-10 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.1s_both]">
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
          <div className="mx-auto max-w-[720px] px-4 py-3 sm:px-8 sm:py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <p className="text-xs text-muted-foreground hidden sm:block">
              确认后大纲冻结，启动&nbsp;4&nbsp;Agent 协作
            </p>
            <div className="flex items-center gap-3 sm:ml-auto">
              <Button
                variant="ghost"
                onClick={handleRegenerate}
                disabled={isGenerating}
                className="flex-1 sm:flex-none text-muted-foreground hover:text-foreground"
              >
                <RefreshCcw className={cn("h-4 w-4", isGenerating && "animate-spin")} />
                <span className="hidden xs:inline sm:inline">重新生成大纲</span>
                <span className="sm:hidden">重新生成</span>
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={isGenerating || confirming || enabledCount === 0}
                size="lg"
                className={cn(
                  "flex-1 sm:flex-none group h-11 px-6 font-medium",
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
        </div>
      )}
    </PageContainer>
  );
}
