"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, Sparkles } from "lucide-react";
import { PageContainer } from "@/components/layout/page-container";
import { DemoWatermark } from "@/components/demo/demo-watermark";
import { useScopingStore } from "@/stores/scoping-store";
import { demoScope } from "@/lib/mocks/demo";
import { cn } from "@/lib/utils";

const DEFAULT_HOLD_MS = 3000;
const REDUCED_HOLD_MS = 800;

export default function DemoScopingPage() {
  const router = useRouter();
  const enterDemoMode = useScopingStore((s) => s.enterDemoMode);

  const headingRef = useRef<HTMLHeadingElement>(null);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(0);

  // Bootstrap demo store + focus the main heading for screen readers.
  useEffect(() => {
    enterDemoMode(demoScope);
    headingRef.current?.focus();
  }, [enterDemoMode]);

  // Drive the progress ring + auto-advance.
  useEffect(() => {
    if (paused) return;
    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const totalMs = reducedMotion ? REDUCED_HOLD_MS : DEFAULT_HOLD_MS;

    const startedAt = performance.now() - progress * totalMs;
    let frame = 0;

    function tick(now: number) {
      const pct = Math.min(1, (now - startedAt) / totalMs);
      setProgress(pct);
      if (pct < 1) {
        frame = requestAnimationFrame(tick);
      } else {
        router.push("/demo/run");
      }
    }

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paused, router]);

  function handleSkip() {
    router.push("/demo/run");
  }

  const coreDims = demoScope.dimensions.filter((d) => d.layer === "core");
  const extDims = demoScope.dimensions.filter((d) => d.layer === "extension");
  const aiSuggestedCount = extDims.filter((d) => d.source === "ai_suggested").length;

  return (
    <>
      <DemoWatermark
        step={1}
        paused={paused}
        onPauseToggle={() => setPaused((p) => !p)}
        onSkip={handleSkip}
      />

      <PageContainer width="narrow">
        <div
          role="status"
          aria-live="polite"
          className="sr-only"
        >
          演示样例 步骤 1 共 3 步：立项预览。3 秒后自动进入 DAG 回放。
        </div>

        <p
          className="mb-4 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          DEMO · Ch. 01 — 立项预览
        </p>

        <h1
          ref={headingRef}
          tabIndex={-1}
          className={cn(
            "text-[1.8rem] leading-[1.05] sm:text-[clamp(2.1rem,4vw,2.8rem)]",
            "tracking-tight text-foreground mb-8",
            "outline-none focus-visible:outline-none",
            "animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_both]",
          )}
          style={{
            fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
            fontWeight: 400,
            textWrap: "balance",
          }}
        >
          ScopingAgent 已生成本次任务的研究契约
        </h1>

        {/* User brief envelope */}
        <section
          aria-label="用户原始 brief"
          className={cn(
            "mb-8 rounded-md border border-border/70 bg-card px-5 py-4",
            "shadow-[0_1px_0_0_oklch(0.88_0.012_75_/_0.6)]",
            "animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.1s_both]",
          )}
        >
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-2">
            用户 Brief
          </p>
          <p className="text-[15px] leading-relaxed text-foreground/90">
            {demoScope.user_brief}
          </p>
        </section>

        {/* Competitor chips */}
        <section
          aria-label="确认的竞品列表"
          className="mb-8 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.2s_both]"
        >
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-3">
            竞品（{demoScope.competitors.length}）
          </p>
          <ul className="flex flex-wrap gap-2">
            {demoScope.competitors.map((name) => (
              <li
                key={name}
                className={cn(
                  "rounded-full border border-border/80 bg-background px-3.5 py-1",
                  "text-sm text-foreground/90",
                )}
              >
                {name}
              </li>
            ))}
          </ul>
        </section>

        {/* Outline */}
        <section
          aria-label="研究大纲"
          className="mb-10 animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.3s_both]"
        >
          <div className="flex items-baseline justify-between mb-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              研究大纲
            </p>
            <p
              className="tabular text-[11px] text-muted-foreground"
              aria-label={`AI 建议扩展维度 ${aiSuggestedCount} of 4`}
            >
              核心 {coreDims.length} · AI 建议 {aiSuggestedCount}/4
            </p>
          </div>

          <ol className="space-y-1.5">
            {demoScope.dimensions.map((d, idx) => (
              <li
                key={d.id}
                className={cn(
                  "flex items-baseline gap-3 rounded-md border border-transparent",
                  "px-3 py-2.5 transition-colors",
                  d.layer === "core"
                    ? "bg-secondary/40"
                    : "bg-card hover:bg-secondary/30",
                )}
              >
                <span className="tabular text-[11px] text-muted-foreground w-6 shrink-0">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span
                  aria-hidden="true"
                  className={cn(
                    "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                    d.layer === "core"
                      ? "bg-secondary text-muted-foreground"
                      : "bg-[var(--color-accent-warm)]/15 text-[var(--color-accent-warm)]",
                  )}
                  title={d.layer === "core" ? "核心层（锁定）" : "扩展层"}
                >
                  {d.layer === "core" ? (
                    <Lock className="h-2.5 w-2.5" />
                  ) : (
                    <Sparkles className="h-2.5 w-2.5" />
                  )}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-[15px] text-foreground/95">{d.title}</p>
                  <p className="text-[12px] text-muted-foreground/90 mt-0.5 leading-relaxed">
                    {d.intent}
                  </p>
                </div>
                <span
                  className="tabular text-[10px] uppercase tracking-[0.15em] text-muted-foreground shrink-0"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {d.source === "system"
                    ? "system"
                    : d.source === "ai_suggested"
                      ? "ai · " + d.id.replace("ext.", "")
                      : "user"}
                </span>
              </li>
            ))}
          </ol>
        </section>

        {/* Progress + auto-advance */}
        <section
          className="rule-fade mb-4"
          aria-hidden="true"
        />

        <footer
          className={cn(
            "flex items-center justify-between gap-4",
            "animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_0.45s_both]",
          )}
        >
          <p className="text-xs text-muted-foreground tabular">
            {paused ? "已暂停" : `自动进入 DAG 回放 · ${Math.ceil((1 - progress) * 3)}s`}
          </p>
          <div
            role="progressbar"
            aria-label="演示自动跳转进度"
            aria-valuenow={Math.round(progress * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            className="h-px flex-1 max-w-[280px] bg-border/60 overflow-hidden rounded-full"
          >
            <div
              className="h-full bg-[var(--color-accent-warm)] transition-[width] duration-100 ease-linear"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
        </footer>
      </PageContainer>
    </>
  );
}
