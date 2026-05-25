"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, PlayCircle } from "lucide-react";
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

// Keywords that signal "skip planning, generate directly"
const DIRECT_ZH = ["直接生成", "直接开始", "直接做", "直接分析", "不要计划", "不要大纲", "不用问", "别问我", "跳过"];
const DIRECT_EN = ["directly", "skip", "no plan", "no outline", "just do it", "don't ask", "generate now", "without plan"];

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
    // Direct-mode currently has no real route; route both branches to the
    // scoping flow until the DAG run page lands. The demo path is reachable
    // via the secondary CTA below.
    router.push(isDirect ? "/demo/scoping" : "/tasks/new/scoping");
  }

  function handleViewDemo() {
    router.push("/demo/scoping");
  }

  return (
    <PageContainer width="narrow">
      {/* Page title */}
      <h1
        className="text-[1.75rem] leading-[1.1] sm:text-[clamp(2rem,4vw,2.75rem)] sm:leading-[1.05] tracking-tight text-foreground mb-10 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_both]"
        style={{
          fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
          fontWeight: 400,
        }}
      >
        {lang === "zh" ? "AI 竞品分析系统" : "AI Competitive Analysis System"}
      </h1>

      {/* The NL brief */}
      <div className="space-y-3 mb-14 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.25s_both]">
        <div className="flex items-baseline justify-between">
          <Label
            htmlFor="brief"
            className="text-sm font-medium uppercase tracking-wider text-foreground"
          >
            <span className="text-destructive mr-1">§</span>
            {lang === "zh" ? "分析需求" : "Analysis Request"}
          </Label>
          <span className="tabular text-xs text-muted-foreground">
            {userBrief.length}&nbsp;{lang === "zh" ? "字" : "chars"}
          </span>
        </div>
        <Textarea
          id="brief"
          value={userBrief}
          onChange={(e) => setUserBrief(e.target.value)}
          placeholder={lang === "zh" ? DEFAULT_BRIEF_PLACEHOLDER : EN_PLACEHOLDER}
          rows={6}
          className={cn(
            "min-h-[180px] resize-y text-base leading-relaxed",
            "bg-card border-border/70 shadow-[0_1px_0_0_oklch(0.88_0.012_75_/_0.6)]",
            "focus-visible:ring-primary/20 focus-visible:border-primary/40",
            "placeholder:text-muted-foreground/60",
            "transition-shadow",
          )}
          autoFocus
        />
      </div>

      <div className="rule-fade mb-8" />

      {/* Submit */}
      <div className="flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.35s_both]">
        <p className="text-xs text-muted-foreground sm:max-w-[34ch]">
          {!canSubmit
            ? lang === "zh"
              ? "描述需求，AI 会自动判断是否先给大纲让你确认。"
              : "Describe your need. AI decides whether to confirm a plan first."
            : isDirect
              ? lang === "zh"
                ? "已识别「直接生成」模式，将跳过大纲确认步骤。"
                : "Direct mode detected — skipping outline confirmation."
              : lang === "zh"
                ? "AI 会先给一份大纲，确认后再开始分析。"
                : "AI will show a draft outline for your approval first."}
        </p>

        <Button
          onClick={handleSubmit}
          disabled={!canSubmit}
          size="lg"
          className={cn(
            "group h-12 w-full sm:w-auto px-7 text-base font-medium",
            "bg-primary text-primary-foreground hover:bg-primary/90",
            "shadow-[0_4px_14px_-4px_oklch(0.38_0.065_220_/_0.4)]",
            "transition-shadow",
            !canSubmit && "shadow-none",
          )}
        >
          {isDirect
            ? lang === "zh" ? "直接分析" : "Analyze Now"
            : lang === "zh" ? "生成大纲" : "Generate Outline"}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </div>

      {/* Secondary CTA — curated demo path for judges / first-time visitors */}
      <div
        className={cn(
          "mt-10 pt-6 border-t border-border/60",
          "flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-3",
          "animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.5s_both]",
        )}
      >
        <p
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {lang === "zh" ? "首次访问 · 评委演示" : "First visit · Demo"}
        </p>
        <button
          type="button"
          onClick={handleViewDemo}
          className={cn(
            "group inline-flex items-center gap-2 text-sm",
            "text-foreground/85 hover:text-foreground",
            "underline decoration-border underline-offset-[6px]",
            "hover:decoration-[var(--color-accent-warm)] transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm",
          )}
        >
          <PlayCircle className="h-4 w-4 text-[var(--color-accent-warm)]" />
          {lang === "zh" ? "30 秒看完整演示" : "Watch 30s demo"}
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </PageContainer>
  );
}
