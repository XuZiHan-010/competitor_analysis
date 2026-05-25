"use client";

import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageContainer } from "@/components/layout/page-container";
import { useScopingStore } from "@/stores/scoping-store";
import { DEFAULT_BRIEF_PLACEHOLDER } from "@/lib/mocks/scope-contract";
import { useLangStore } from "@/stores/lang-store";
import { cn } from "@/lib/utils";

const EN_PLACEHOLDER =
  "e.g. Compare SK-II, Shiseido, and Estée Lauder on membership programs and KOL strategy in Chinese e-commerce…";

const DIRECT_ZH = ["直接生成", "直接开始", "直接做", "直接分析", "不要计划", "不要大纲", "不用问", "别问我", "跳过"];
const DIRECT_EN = ["directly", "skip", "no plan", "no outline", "just do it", "don't ask", "generate now", "without plan"];

const EXAMPLE_BRIEFS = [
  {
    label: "Trae · AI 编程",
    text: "对比 Trae、Cursor、GitHub Copilot 在 AI 编程辅助功能上的差异，重点关注开发者体验、代码补全质量与企业版定价策略。",
  },
  {
    label: "飞书 · 企业协作",
    text: "分析飞书、钉钉、企业微信在企业协作市场的功能差异、定价策略与大客户渗透率，重点关注中大型企业市场。",
  },
  {
    label: "抖音 · 内容电商",
    text: "对比抖音、快手、微信视频号在内容电商和创作者变现机制上的差异，评估品牌方投放效率与私域运营策略。",
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

      {/* ── 区段 1: 页面掌头 ── */}
      <div className="mb-12">
        {/* Two-line display headline */}
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
                多 Agent 竞品情报平台
              </span>
            </>
          ) : (
            <>
              Strata AI
              <span className="block mt-2 text-[1.5rem] sm:text-[clamp(1.75rem,3.5vw,2.5rem)] leading-[1.1]">
                Multi-Agent Competitive Intelligence
              </span>
            </>
          )}
        </h1>
      </div>

      {/* 掌头分隔线 */}
      <div className="rule-fade mb-10 animate-[fade-in_0.6s_ease-out_0.2s_both]" />

      {/* ── 区段 2: 需求输入 ── */}
      <div className="mb-8 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.3s_both]">

        {/* 指引文字 */}
        <Label
          htmlFor="brief"
          className="block text-sm text-[#374151] leading-relaxed mb-4"
        >
          {lang === "zh"
            ? "描述你的竞品分析需求。默认情况下，Strata 会先生成研究大纲供你确认；如果需求已经足够明确，或你明确要求直接生成报告，Strata 将跳过大纲直接开始分析。"
            : "Describe your competitive analysis request. By default, Strata will first generate a research outline for your review; if your request is already specific enough, or you explicitly ask for the report directly, Strata will skip the outline and begin analysis."}
        </Label>

        {/* Textarea + 字数计数 */}
        <div className="relative">
          <Textarea
            id="brief"
            name="brief"
            autoComplete="off"
            value={userBrief}
            onChange={(e) => setUserBrief(e.target.value)}
            placeholder={lang === "zh" ? DEFAULT_BRIEF_PLACEHOLDER : EN_PLACEHOLDER}
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
              {userBrief.length}&nbsp;{lang === "zh" ? "字" : "chars"}
            </span>
          )}
        </div>

        {/* 示例快填 Chips（仅中文模式显示） */}
        {lang === "zh" && (
          <div className="mt-3 flex flex-wrap gap-2 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.45s_both]">
            {EXAMPLE_BRIEFS.map((ex) => (
              <button
                key={ex.label}
                type="button"
                onClick={() => handleExampleClick(ex.text)}
                aria-label={`填入示例：${ex.label}`}
                className={cn(
                  "rounded-full border border-border/70 px-3 py-1 text-sm",
                  "text-foreground hover:bg-secondary/80",
                  "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                )}
              >
                {ex.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── 区段 3: 操作行 ── */}
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
          {isDirect
            ? lang === "zh" ? "直接分析" : "Analyze Now"
            : lang === "zh" ? "生成研究计划" : "Generate Research Plan"}
          <ArrowRight aria-hidden="true" className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </div>


    </PageContainer>
  );
}
