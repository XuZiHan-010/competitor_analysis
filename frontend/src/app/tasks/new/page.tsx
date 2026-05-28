"use client";

import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageContainer } from "@/components/layout/page-container";
import { useScopingStore } from "@/stores/scoping-store";
import { useLangStore } from "@/stores/lang-store";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const DIRECT_ZH = ["直接生成", "直接开始", "直接做", "直接分析", "不要计划", "不要大纲", "不用问", "别问我", "跳过"];
const DIRECT_EN = ["directly", "skip", "no plan", "no outline", "just do it", "don't ask", "generate now", "without plan"];

const EXAMPLE_BRIEFS = [
  {
    zh: {
      label: "Trae · AI 编程",
      text: "对比 Trae、Cursor、GitHub Copilot 在 AI 编程辅助功能上的差异，重点关注开发者体验、代码补全质量与企业版定价策略。",
    },
    en: {
      label: "Trae · AI Coding",
      text: "Compare Trae, Cursor, and GitHub Copilot across AI coding assistance, focusing on developer experience, completion quality, and enterprise pricing.",
    },
  },
  {
    zh: {
      label: "飞书 · 企业协作",
      text: "分析飞书、钉钉、企业微信在企业协作市场的功能差异、定价策略与大客户渗透率，重点关注中大型企业市场。",
    },
    en: {
      label: "Lark · Collaboration",
      text: "Analyze Lark, DingTalk, and WeCom in enterprise collaboration, focusing on feature differences, pricing strategy, and large-account penetration.",
    },
  },
  {
    zh: {
      label: "抖音 · 内容电商",
      text: "对比抖音、快手、微信视频号在内容电商和创作者变现机制上的差异，评估品牌方投放效率与私域运营策略。",
    },
    en: {
      label: "Douyin · Commerce",
      text: "Compare Douyin, Kuaishou, and WeChat Channels across content commerce and creator monetization, then evaluate brand ad efficiency and private-domain strategy.",
    },
  },
];


function classifyIntent(brief: string): "direct" | "plan" {
  const lower = brief.toLowerCase();
  if (DIRECT_ZH.some((kw) => brief.includes(kw))) return "direct";
  if (DIRECT_EN.some((kw) => lower.includes(kw))) return "direct";
  return "plan";
}

export default function NewTaskPage() {
  const router = useRouter();
  const { lang } = useLangStore();
  const { t } = useI18n();
  const { userBrief, setUserBrief } = useScopingStore();

  const canSubmit = userBrief.trim().length > 0;
  const isDirect = canSubmit && classifyIntent(userBrief) === "direct";

  function handleSubmit() {
    if (!canSubmit) return;
    router.push(isDirect ? "/demo/scoping" : "/tasks/new/scoping");
  }

  function handleExampleClick(text: string) {
    setUserBrief(text);
    setTimeout(() => {
      (document.getElementById("brief") as HTMLTextAreaElement | null)?.focus();
    }, 0);
  }

  return (
    <PageContainer width="narrow">

      <div className="mb-12">
        <h1
          className={cn(
            "text-[2.25rem] leading-[0.97] sm:text-[clamp(2.75rem,6vw,4rem)] sm:leading-[0.95]",
            "tracking-tight text-[#1F2933] [text-wrap:balance]",
            "animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.1s_both]",
          )}
          style={{
            fontFamily: "var(--font-display)",
            fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
            fontWeight: 400,
          }}
        >
          {lang === "zh" ? (
            <>
              Strata AI
              <span className="block mt-2 text-[1.5rem] sm:text-[clamp(1.75rem,3.5vw,2.5rem)] leading-[1.1]">
                {t("taskHeadline")}
              </span>
            </>
          ) : (
            <>
              Strata AI
              <span className="block mt-2 text-[1.5rem] sm:text-[clamp(1.75rem,3.5vw,2.5rem)] leading-[1.1]">
                {t("taskHeadline")}
              </span>
            </>
          )}
        </h1>
      </div>

      <div className="rule-fade mb-10 animate-[fade-in_0.6s_ease-out_0.2s_both]" />

      <div className="mb-8 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.3s_both]">
        <Label
          htmlFor="brief"
          className="block text-sm text-[#374151] leading-relaxed mb-4"
        >
          {t("taskIntro")}
        </Label>

        <div className="relative">
          <Textarea
            id="brief"
            name="brief"
            autoComplete="off"
            value={userBrief}
            onChange={(e) => setUserBrief(e.target.value)}
            placeholder={t("taskPlaceholder")}
            rows={6}
            className={cn(
              "min-h-[220px] resize-none text-base leading-relaxed pb-8",
              "bg-card border-border/70 shadow-[0_1px_0_0_oklch(0.88_0.012_75_/_0.6)]",
              "focus-visible:ring-[var(--color-accent-warm)]/25 focus-visible:border-[var(--color-accent-warm)]/45",
              "placeholder:text-[#A3A3A3]",
              "transition-[border-color,box-shadow]",
            )}
            autoFocus
          />
          {userBrief.length > 0 && (
            <span className="pointer-events-none absolute bottom-2.5 right-3 select-none text-[10px] tabular text-muted-foreground/50">
              {userBrief.length}&nbsp;{t("charUnit")}
            </span>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-2 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.45s_both]">
          {EXAMPLE_BRIEFS.map((example) => {
            const ex = example[lang];
            return (
              <button
                key={ex.label}
                type="button"
                onClick={() => handleExampleClick(ex.text)}
                aria-label={t("fillExample", { label: ex.label })}
                className={cn(
                  "rounded-full border border-border/70 px-3 py-1 text-sm",
                  "text-foreground hover:bg-secondary/80",
                  "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                )}
              >
                {ex.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex justify-end animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.5s_both]">
        <Button
          onClick={handleSubmit}
          disabled={!canSubmit}
          size="lg"
          className={cn(
            "group h-11 w-full sm:w-auto px-8 text-base font-medium",
            "bg-primary text-primary-foreground hover:bg-primary/90",
            "shadow-[0_4px_14px_-4px_oklch(0.38_0.065_220_/_0.4)]",
            "transition-shadow",
            !canSubmit && "shadow-none",
          )}
        >
          {isDirect ? t("analyzeNow") : t("generatePlan")}
          <ArrowRight aria-hidden="true" className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </div>


    </PageContainer>
  );
}
