"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { switchReportLanguage, type Report } from "@/lib/api/reports";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

interface ReportLanguageToggleProps {
  taskId: string;
  /** Current report-content language (distinct from UI i18n language). */
  value: "zh" | "en";
  onSwitched: (report: Report) => void;
}

const OPTIONS: { lang: "zh" | "en"; label: string }[] = [
  { lang: "zh", label: "中文" },
  { lang: "en", label: "EN" },
];

/**
 * Switches the report *content* language by regenerating the localized version
 * on the backend (preserving claims/source_ids). Separate from the global UI
 * LangToggle, which only swaps interface strings.
 */
export function ReportLanguageToggle({ taskId, value, onSwitched }: ReportLanguageToggleProps) {
  const { t } = useI18n();
  const [pending, setPending] = useState<"zh" | "en" | null>(null);

  async function switchTo(lang: "zh" | "en") {
    if (lang === value || pending) return;
    setPending(lang);
    try {
      const updated = await switchReportLanguage(taskId, lang);
      onSwitched(updated);
    } catch {
      toast.error(t("reportLangError"));
    } finally {
      setPending(null);
    }
  }

  return (
    <div
      role="group"
      aria-label={t("reportLangLabel")}
      aria-busy={pending !== null}
      className="inline-flex items-center rounded border border-border/70 p-0.5"
      style={{ fontFamily: "var(--font-mono)" }}
    >
      {OPTIONS.map(({ lang, label }) => {
        const active = lang === value;
        const isPending = pending === lang;
        return (
          <button
            key={lang}
            type="button"
            onClick={() => switchTo(lang)}
            aria-pressed={active}
            disabled={pending !== null || active}
            className={cn(
              "inline-flex items-center gap-1 rounded-sm px-2.5 py-1 text-[12px] transition-colors",
              "focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground disabled:opacity-60",
            )}
          >
            {isPending && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
            {label}
          </button>
        );
      })}
    </div>
  );
}
