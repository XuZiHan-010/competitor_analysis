"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageContainer } from "@/components/layout/page-container";
import { useScopingStore } from "@/stores/scoping-store";
import { buildEmptyDraftContract } from "@/lib/mocks/scope-contract";
import { CompetitorChips } from "@/components/scoping/competitor-chips";
import { DimensionList } from "@/components/scoping/dimension-list";
import { AddDimensionDialog } from "@/components/scoping/add-dimension-dialog";
import { ReguideInput } from "@/components/scoping/reguide-input";
import { CollapsibleSection } from "@/components/scoping/collapsible-section";
import { UserResearchCard } from "@/components/scoping/user-research-card";
import { useI18n } from "@/lib/i18n";
import { createScopingDraft } from "@/lib/api/scoping";
import { startTaskRun } from "@/lib/api/tasks";
import { cn } from "@/lib/utils";

export default function ScopingPage() {
  const router = useRouter();
  const {
    userBrief,
    manualCompetitors,
    draftContract,
    isGenerating,
    setDraftContract,
    setIsGenerating,
  } = useScopingStore();

  const [confirming, setConfirming] = useState(false);
  const { lang, t } = useI18n();

  useEffect(() => {
    if (draftContract && draftContract.user_brief === userBrief) return;

    let mounted = true;
    setIsGenerating(true);
    setDraftContract(null);
    createScopingDraft({
      userBrief,
      knownCompetitors: manualCompetitors,
    })
      .then(({ contract }) => {
        if (mounted) setDraftContract(contract);
      })
      .catch(() => {
        if (!mounted) return;
        setDraftContract(buildEmptyDraftContract(userBrief));
        toast.error("ScopingAgent 暂时不可用", {
          description: "已切换为空白研究契约，可手动补齐竞品后继续。",
        });
      })
      .finally(() => {
        if (mounted) setIsGenerating(false);
      });

    return () => {
      mounted = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userBrief]);

  async function handleConfirm() {
    if (!draftContract) return;
    setConfirming(true);
    const frozenContract = {
      ...draftContract,
      frozen_at: new Date().toISOString(),
    };
    setDraftContract(frozenContract);

    try {
      const run = await startTaskRun(frozenContract);
      toast.success(t("taskCreated"), {
        description: t("taskCreatedDescription"),
      });
      router.push(`/tasks/${run.id}`);
    } catch {
      toast.error("任务启动失败", {
        description: "请确认至少保留 3 个竞品，并检查后端服务是否可用。",
      });
      setConfirming(false);
    }
  }

  const enabledCount =
    draftContract?.dimensions.filter((dimension) => dimension.enabled).length ?? 0;
  const totalCount = draftContract?.dimensions.length ?? 0;
  const competitorCount = draftContract?.competitors.length ?? 0;

  return (
    <PageContainer width="narrow" className="pb-32">
      <div className="mb-8 flex animate-[fade-in_0.4s_ease-out] items-baseline gap-3">
        <Link
          href="/tasks/new"
          className="inline-flex items-center gap-1 text-xs uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          <ArrowLeft className="h-3 w-3" />
          {t("rewriteBrief")}
        </Link>
        <span className="h-px flex-1 bg-border" />
        <span
          className="tabular text-xs uppercase tracking-[0.22em] text-primary"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {t("scopingStatus")}
        </span>
      </div>

      <h1 className="sr-only">{t("scopingTitle")}</h1>

      {isGenerating && !draftContract && (
        <div className="flex animate-[fade-in_0.3s_ease-out] flex-col items-center justify-center gap-4 py-24">
          <Sparkles
            className="h-8 w-8 animate-[thinking-pulse_2s_ease-in-out_infinite] text-primary"
            strokeWidth={1.5}
          />
          <p
            className="animate-[thinking-pulse_2s_ease-in-out_infinite] text-sm uppercase tracking-[0.22em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {t("scopingLoading")}
          </p>
        </div>
      )}

      {draftContract && (
        <>
          <section className="mb-10 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.05s_both]">
            <p className="mb-6 max-w-[52ch] text-base leading-relaxed text-muted-foreground">
              {lang === "zh" ? (
                <>
                  {t("scopingIntroBefore")}
                  <span className="tabular mx-1 font-medium text-foreground">
                    4&nbsp;{t("scopingCore")}
                  </span>
                  {t("scopingMiddle")}
                  <span className="tabular mx-1 font-medium text-foreground">
                    {Math.max(0, totalCount - 4)}&nbsp;{t("scopingExtension")}
                  </span>
                  {t("scopingIntroAfter")}
                </>
              ) : (
                <>
                  {t("scopingIntroBefore")}{" "}
                  <span className="tabular font-medium text-foreground">
                    4 {t("scopingCore")}
                  </span>{" "}
                  {t("scopingMiddle")}{" "}
                  <span className="tabular font-medium text-foreground">
                    {Math.max(0, totalCount - 4)} {t("scopingExtension")}
                  </span>{" "}
                  {t("scopingIntroAfter")}
                </>
              )}
            </p>
            <CompetitorChips />
          </section>

          <div className="mb-10 space-y-4 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.15s_both]">
            <CollapsibleSection
              title={t("outlineTitle")}
              defaultOpen
              badge={
                <span
                  className="tabular text-xs text-muted-foreground"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {enabledCount} / {totalCount} {t("enabled")}
                </span>
              }
            >
              <p className="mb-4 text-xs italic text-muted-foreground">
                {t("outlineTip")}
              </p>

              <div
                className={cn(
                  "transition-opacity",
                  isGenerating && "pointer-events-none opacity-50",
                )}
              >
                <DimensionList dimensions={draftContract.dimensions} />
              </div>

              <div className="mt-3">
                <AddDimensionDialog />
              </div>

              <ReguideInput />
            </CollapsibleSection>

            <CollapsibleSection
              title="用户研究计划"
              accent
              defaultOpen={false}
              badge={
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-[10px] uppercase tracking-[0.12em]",
                    draftContract.user_research_plan.enabled
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground/70",
                  )}
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {draftContract.user_research_plan.enabled ? "已启用" : "未启用"}
                </span>
              }
            >
              <UserResearchCard
                value={draftContract.user_research_plan}
                onChange={(plan) =>
                  setDraftContract({ ...draftContract, user_research_plan: plan })
                }
                contractId={draftContract.task_id}
                competitors={draftContract.competitors}
              />
            </CollapsibleSection>
          </div>
        </>
      )}

      {draftContract && (
        <div
          className={cn(
            "fixed bottom-0 left-0 right-0 z-30",
            "border-t border-border bg-background/95 backdrop-blur",
            "supports-[backdrop-filter]:bg-background/85",
          )}
        >
          <div className="mx-auto flex max-w-[720px] justify-end px-4 py-3 sm:px-8 sm:py-4">
            <Button
              onClick={handleConfirm}
              disabled={
                isGenerating ||
                confirming ||
                enabledCount === 0 ||
                competitorCount < 1
              }
              size="lg"
              className={cn(
                "group h-11 w-full px-6 font-medium sm:w-auto",
                "bg-primary text-primary-foreground hover:bg-primary/90",
                "shadow-[0_4px_14px_-4px_oklch(0.38_0.065_220_/_0.4)]",
              )}
            >
              {confirming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  {t("confirmAnalysis")}
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
