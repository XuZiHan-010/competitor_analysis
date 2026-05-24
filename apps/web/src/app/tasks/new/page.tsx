"use client";

import { useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageContainer } from "@/components/layout/page-container";
import { useScopingStore } from "@/stores/scoping-store";
import { DEFAULT_BRIEF_PLACEHOLDER } from "@/lib/mocks/scope-contract";
import { useLangStore } from "@/stores/lang-store";
import { cn } from "@/lib/utils";

const EN_PLACEHOLDER =
  "e.g. Compare SK-II, Shiseido, and Estée Lauder on membership programs and KOL strategy in Chinese e-commerce, focusing on urban female consumers aged 25-35.";

export default function NewTaskPage() {
  const router = useRouter();
  const { lang } = useLangStore();
  const {
    userBrief,
    manualCompetitors,
    setUserBrief,
    addManualCompetitor,
    removeManualCompetitor,
  } = useScopingStore();

  const [chipDraft, setChipDraft] = useState("");

  const canSubmit = userBrief.trim().length > 0;

  function handleChipKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const name = chipDraft.trim();
      if (name) {
        addManualCompetitor(name);
        setChipDraft("");
      }
    } else if (e.key === "Backspace" && !chipDraft && manualCompetitors.length) {
      removeManualCompetitor(manualCompetitors[manualCompetitors.length - 1]);
    }
  }

  function handleSubmit() {
    if (!canSubmit) return;
    router.push("/tasks/new/scoping");
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
      <div className="space-y-3 mb-10 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.25s_both]">
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

      {/* Optional competitor chips */}
      <div className="space-y-3 mb-12 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.35s_both]">
        <div className="flex items-baseline justify-between">
          <Label
            htmlFor="competitors"
            className="text-sm font-medium uppercase tracking-wider text-foreground"
          >
            {lang === "zh" ? "竞品名称" : "Competitors"}{" "}
            <span className="ml-2 text-xs normal-case tracking-normal text-muted-foreground font-normal">
              {lang === "zh"
                ? "可选 · 不填会从上方需求自动提取"
                : "Optional · Auto-extracted from your request above"}
            </span>
          </Label>
          {manualCompetitors.length > 0 && (
            <span className="tabular text-xs text-muted-foreground">
              {manualCompetitors.length}&nbsp;{lang === "zh" ? "项" : "items"}
            </span>
          )}
        </div>

        <div
          className={cn(
            "flex flex-wrap items-center gap-2 px-3 py-2.5",
            "bg-card border border-border/70 rounded-md",
            "shadow-[0_1px_0_0_oklch(0.88_0.012_75_/_0.6)]",
            "focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/20",
            "transition-shadow",
          )}
        >
          {manualCompetitors.map((name) => (
            <span
              key={name}
              className={cn(
                "group inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1",
                "bg-secondary text-secondary-foreground text-sm rounded",
                "border border-border/60",
                "animate-[fade-in_0.2s_ease-out]",
              )}
            >
              <span>{name}</span>
              <button
                type="button"
                onClick={() => removeManualCompetitor(name)}
                className="rounded-sm p-0.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                aria-label={`移除 ${name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          <input
            id="competitors"
            name="competitors"
            type="text"
            value={chipDraft}
            onChange={(e) => setChipDraft(e.target.value)}
            onKeyDown={handleChipKey}
            placeholder={
              manualCompetitors.length === 0
                ? lang === "zh"
                  ? "输入名称后按 Enter 添加…"
                  : "Type a name and press Enter to add..."
                : ""
            }
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            aria-label="添加竞品名称"
            className="flex-1 min-w-[140px] bg-transparent outline-none text-sm placeholder:text-muted-foreground/60"
          />
        </div>

        {chipDraft && (
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Plus className="h-3 w-3" />
            {lang === "zh" ? `按 Enter 添加「${chipDraft}」` : `Press Enter to add "${chipDraft}"`}
          </p>
        )}
      </div>

      <div className="rule-fade mb-8" />

      {/* Submit */}
      <div className="flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.45s_both]">
        <p className="text-xs text-muted-foreground sm:max-w-[28ch]">
          {lang === "zh"
            ? "下一步：AI 会基于需求生成大纲并提出补充问题，你可以编辑后再开始分析。"
            : "Next: AI will generate an outline and ask clarifying questions. You can edit before starting."}
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
          {lang === "zh" ? "生成大纲" : "Generate Outline"}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </div>
    </PageContainer>
  );
}
