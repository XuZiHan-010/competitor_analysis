"use client";

import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { PageContainer } from "@/components/layout/page-container";
import { SearchResultCard } from "@/components/report/search-result-card";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";
import {
  searchReports,
  type ReportSearchMode,
  type ReportSearchResultItem,
} from "@/lib/api/reports";
import { cn } from "@/lib/utils";

type Status = "idle" | "loading" | "ready" | "error";

const DEBOUNCE_MS = 300;

export default function ReportSearchPage() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<ReportSearchResultItem[]>([]);
  const [mode, setMode] = useState<ReportSearchMode | null>(null);
  const seq = useRef(0);

  // Debounced fetch. State is only set inside the async timeout callback —
  // synchronous transitions (idle reset / loading) live in the change handler.
  useEffect(() => {
    const term = query.trim();
    if (!term) return;
    const requestId = seq.current;
    const timer = window.setTimeout(() => {
      searchReports(term)
        .then((res) => {
          if (requestId !== seq.current) return; // stale response, ignore
          setResults(res.results);
          setMode(res.mode);
          setStatus("ready");
        })
        .catch(() => {
          if (requestId !== seq.current) return;
          setStatus("error");
        });
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  function handleChange(value: string) {
    seq.current += 1; // invalidate any in-flight request
    setQuery(value);
    if (value.trim()) {
      setStatus("loading");
    } else {
      setStatus("idle");
      setResults([]);
      setMode(null);
    }
  }

  return (
    <PageContainer width="wide">
      <header className="mb-8">
        <p
          className="mb-3 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          竞品分析 · 历史检索
        </p>
        <h1
          className="text-[2.4rem] leading-[1.05] tracking-tight text-foreground"
          style={{
            fontFamily: "var(--font-display)",
            fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
            fontWeight: 380,
            textWrap: "balance",
          }}
        >
          {t("searchTitle")}
        </h1>

        {/* Search field */}
        <div className="relative mt-6 max-w-[640px]">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/60"
            aria-hidden="true"
          />
          <Input
            type="search"
            name="q"
            autoComplete="off"
            enterKeyHint="search"
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={t("searchPlaceholder")}
            aria-label={t("searchTitle")}
            autoFocus
            className="h-11 rounded-lg pl-9 text-base"
          />
        </div>

        <div className="rule-fade mt-7" aria-hidden="true" />
      </header>

      {/* Result mode + count strip */}
      {status === "ready" && (
        <div
          className="mb-4 flex items-center gap-3 text-[10px] uppercase tracking-[0.18em] text-muted-foreground/60"
          style={{ fontFamily: "var(--font-mono)" }}
          aria-live="polite"
        >
          {mode && (
            <span
              className={cn(
                "inline-flex items-center rounded border px-1.5 py-0.5",
                mode === "pgvector"
                  ? "border-primary/40 bg-primary/8 text-primary"
                  : "border-border/60 text-muted-foreground/70",
              )}
            >
              {mode === "pgvector" ? t("searchModePgvector") : t("searchModeKeyword")}
            </span>
          )}
          <span className="tabular">
            {results.length} {results.length === 1 ? "match" : "matches"}
          </span>
        </div>
      )}

      {status === "idle" ? (
        <IdleState hint={t("searchIdle")} />
      ) : status === "loading" ? (
        <ResultsSkeleton />
      ) : status === "error" ? (
        <p className="text-sm text-destructive" role="alert">
          {t("searchError")}
        </p>
      ) : results.length === 0 ? (
        <EmptyState hint={t("searchEmpty")} />
      ) : (
        <ol className="space-y-2" aria-label={t("searchTitle")}>
          {results.map((item) => (
            <SearchResultCard key={item.report_id} item={item} query={query} />
          ))}
        </ol>
      )}
    </PageContainer>
  );
}

function IdleState({ hint }: { hint: string }) {
  return (
    <div className="flex flex-col items-center gap-4 py-20 text-center">
      <Search className="h-7 w-7 text-muted-foreground/40" aria-hidden="true" />
      <p
        className="max-w-[420px] text-[11px] uppercase leading-relaxed tracking-[0.18em] text-muted-foreground/70"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {hint}
      </p>
    </div>
  );
}

function EmptyState({ hint }: { hint: string }) {
  return (
    <div className="rounded-md border border-dashed border-border/60 py-20 text-center">
      <p
        className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground/70"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {hint}
      </p>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="h-[104px] rounded-md border border-border/60 bg-card/40 animate-pulse"
          style={{ opacity: 1 - i * 0.18 }}
        />
      ))}
    </div>
  );
}
