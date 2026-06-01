"use client";

import { useState, type KeyboardEvent } from "react";
import { CornerDownLeft, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useScopingStore } from "@/stores/scoping-store";
import { createScopingDraft } from "@/lib/api/scoping";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function ReguideInput() {
  const draftContract = useScopingStore((state) => state.draftContract);
  const isGenerating = useScopingStore((state) => state.isGenerating);
  const setDraftContract = useScopingStore((state) => state.setDraftContract);
  const setIsGenerating = useScopingStore((state) => state.setIsGenerating);
  const { t } = useI18n();

  const [guidance, setGuidance] = useState("");
  const [focused, setFocused] = useState(false);

  if (!draftContract) return null;

  const trimmed = guidance.trim();
  const canSubmit = trimmed.length > 0 && !isGenerating;

  async function apply() {
    if (!canSubmit || !draftContract) return;
    const augmentedBrief = `${draftContract.user_brief}\n\n[补充指导]: ${trimmed}`;

    setIsGenerating(true);
    try {
      const { contract } = await createScopingDraft({
        userBrief: augmentedBrief,
        knownCompetitors: draftContract.competitors,
      });
      setDraftContract(contract);
      setGuidance("");
      toast.success(t("reguideSuccess"), {
        description: t("reguideSuccessDescription"),
      });
    } catch {
      toast.error("重新生成失败", {
        description: "后端 ScopingAgent 暂时不可用，当前大纲已保留。",
      });
    } finally {
      setIsGenerating(false);
    }
  }

  function onKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      apply();
    }
  }

  return (
    <section
      aria-label={t("reguideAria")}
      className="mt-10 animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_0.2s_both]"
    >
      <div
        className={cn(
          "overflow-hidden rounded-lg border bg-card",
          "transition-[border-color,box-shadow] duration-200",
          focused
            ? "border-primary/50 shadow-[0_0_0_4px_oklch(0.38_0.065_220_/_0.08)]"
            : "border-border/70 hover:border-border",
        )}
      >
        <textarea
          id="reguide-input"
          name="reguide"
          value={guidance}
          onChange={(event) => setGuidance(event.target.value)}
          onKeyDown={onKey}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={isGenerating}
          rows={1}
          placeholder={t("reguidePlaceholder")}
          spellCheck={false}
          aria-describedby="reguide-help"
          className={cn(
            "block w-full resize-none bg-transparent outline-none",
            "px-4 py-3 text-sm leading-relaxed",
            "placeholder:text-muted-foreground/55 placeholder:italic",
            "[field-sizing:content] max-h-[180px] min-h-[44px]",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        />

        <div
          className={cn(
            "flex items-center justify-between gap-3 px-3 py-2",
            "border-t border-border/40 bg-muted/25",
          )}
        >
          <label
            htmlFor="reguide-input"
            className="tabular inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.2em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <Sparkles className="h-3 w-3" strokeWidth={1.75} />
            {t("reguideLabel")}
          </label>

          <div className="flex items-center gap-2.5">
            <span
              id="reguide-help"
              className="tabular hidden items-center gap-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground/55 sm:inline-flex"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              <kbd className="rounded border border-border/60 bg-background/60 px-1 py-0.5 text-[10px] leading-none">
                Ctrl
              </kbd>
              <kbd className="inline-flex items-center rounded border border-border/60 bg-background/60 px-1 py-0.5 text-[10px] leading-none">
                <CornerDownLeft className="h-2.5 w-2.5" />
              </kbd>
            </span>

            <Button
              type="button"
              onClick={apply}
              disabled={!canSubmit}
              size="sm"
              variant="ghost"
              className={cn(
                "h-7 px-2.5 text-xs font-medium",
                "border transition-colors",
                canSubmit
                  ? "border-primary/40 text-primary hover:border-primary/70 hover:bg-primary/10"
                  : "border-border/40 text-muted-foreground/50",
              )}
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {t("regenerating")}
                </>
              ) : (
                <>
                  {t("applyReguide")}
                  <CornerDownLeft className="h-3 w-3" />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
