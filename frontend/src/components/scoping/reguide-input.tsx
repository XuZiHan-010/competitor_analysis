"use client";

import { useState, type KeyboardEvent } from "react";
import { CornerDownLeft, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useScopingStore } from "@/stores/scoping-store";
import { jitteredThinking } from "@/lib/mocks/delay";
import { buildSkincareMockContract } from "@/lib/mocks/scope-contract";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function ReguideInput() {
  const draftContract = useScopingStore((s) => s.draftContract);
  const isGenerating = useScopingStore((s) => s.isGenerating);
  const setDraftContract = useScopingStore((s) => s.setDraftContract);
  const setIsGenerating = useScopingStore((s) => s.setIsGenerating);
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
    await jitteredThinking(1800, 500);
    setDraftContract(
      buildSkincareMockContract(augmentedBrief, draftContract.competitors),
    );
    setIsGenerating(false);
    setGuidance("");
    toast.success(t("reguideSuccess"), {
      description: t("reguideSuccessDescription"),
    });
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
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
          "rounded-lg border bg-card overflow-hidden",
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
          onChange={(e) => setGuidance(e.target.value)}
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
            "[field-sizing:content] min-h-[44px] max-h-[180px]",
            "disabled:opacity-50 disabled:cursor-not-allowed",
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
            className="tabular text-[11px] uppercase tracking-[0.2em] text-muted-foreground inline-flex items-center gap-1.5"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <Sparkles className="h-3 w-3" strokeWidth={1.75} />
            {t("reguideLabel")}
          </label>

          <div className="flex items-center gap-2.5">
            <span
              id="reguide-help"
              className="tabular text-[10px] uppercase tracking-[0.18em] text-muted-foreground/55 hidden sm:inline-flex items-center gap-1"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              <kbd className="px-1 py-0.5 rounded border border-border/60 bg-background/60 text-[10px] leading-none">
                ⌘
              </kbd>
              <kbd className="px-1 py-0.5 rounded border border-border/60 bg-background/60 text-[10px] leading-none inline-flex items-center">
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
                  ? "border-primary/40 text-primary hover:bg-primary/8 hover:border-primary/70"
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
