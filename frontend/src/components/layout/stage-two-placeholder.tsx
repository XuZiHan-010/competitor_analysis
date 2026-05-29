"use client";

import Link from "next/link";
import { ArrowLeft, Construction } from "lucide-react";
import { PageContainer } from "./page-container";
import { useI18n, type TranslationKey } from "@/lib/i18n";

interface StageTwoPlaceholderProps {
  label?: string;
  labelKey?: TranslationKey;
  blurb?: string;
  blurbKey?: TranslationKey;
  /** Route for the back link. Defaults to /tasks/new. */
  backHref?: string;
  backLabel?: string;
  backLabelKey?: TranslationKey;
}

/**
 * A consistent placeholder shown by Stage 2 pages (DAG, report,
 * report list, login) until they're built. Keeps the editorial tone
 * so navigation feels intentional rather than 404-broken.
 */
export function StageTwoPlaceholder({
  label,
  labelKey,
  blurb,
  blurbKey,
  backHref = "/tasks/new",
  backLabel,
  backLabelKey,
}: StageTwoPlaceholderProps) {
  const { t } = useI18n();
  const displayLabel = labelKey ? t(labelKey) : (label ?? "");
  const displayBlurb = blurbKey ? t(blurbKey) : (blurb ?? "");
  const displayBackLabel = backLabelKey
    ? t(backLabelKey)
    : (backLabel ?? t("stageBackDefault"));

  return (
    <PageContainer width="narrow" className="py-24">
      <div className="flex items-baseline gap-3 mb-10">
        <span
          className="tabular text-xs uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {t("stageStatus")}
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="flex items-start gap-5 mb-8">
        <span
          className="inline-flex items-center justify-center h-10 w-10 rounded border border-accent-warm/30"
          style={{ color: "var(--accent-warm)" }}
        >
          <Construction className="h-5 w-5" strokeWidth={1.5} />
        </span>
        <div>
          <h1
            className="text-[clamp(1.75rem,3.5vw,2.5rem)] leading-[1.1] tracking-tight text-foreground"
            style={{
              fontVariationSettings: '"opsz" 144',
              fontWeight: 400,
            }}
          >
            {displayLabel}
          </h1>
        </div>
      </div>

      <p className="text-base text-muted-foreground leading-relaxed max-w-[44ch] mb-12">
        {displayBlurb}
      </p>

      <div className="rule-fade mb-10" />

      <Link
        href={backHref}
        className="inline-flex items-center gap-1.5 text-sm text-primary hover:text-primary/80 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {displayBackLabel}
      </Link>
    </PageContainer>
  );
}
