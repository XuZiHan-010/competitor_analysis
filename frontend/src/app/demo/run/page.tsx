"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { PageContainer } from "@/components/layout/page-container";
import { DemoWatermark } from "@/components/demo/demo-watermark";
import {
  fallbackDemoReplayBundle,
  fetchDemoReplayBundle,
} from "@/lib/api/demo";
import type { DemoTraceEvent } from "@/lib/mocks/demo/types";
import { DagGraph } from "@/components/dag/dag-graph";
import type { AgentNodeStatus, DagNodeView } from "@/components/dag/types";
import { cn } from "@/lib/utils";

const DEMO_PIPELINE = [
  { agent: "CollectorAgent", label: "Collector", role: "公开数据采集 + 溯源" },
  { agent: "AnalystAgent", label: "Analyst", role: "Schema 抽取 + 结构化" },
  { agent: "WriterAgent", label: "Writer", role: "章节渲染 + 摘要" },
  { agent: "QAAgent", label: "QA", role: "字段校验 + 反馈闭环" },
] as const;

const COMPRESS_FACTOR_REDUCED = 0.2; // play at 5× when prefers-reduced-motion

/**
 * Folds the replay event stream into the shared DAG view model. A QA `blocker`
 * that has not yet been `resolved` puts QA in `warn` and Collector in `retrying`
 * (mirroring the live page); each blocker counts as one Collector re-run.
 */
function computeDemoNodes(fired: DemoTraceEvent[]): DagNodeView[] {
  const base: Record<string, "idle" | "running" | "done" | "warn"> = {
    CollectorAgent: "idle",
    AnalystAgent: "idle",
    WriterAgent: "idle",
    QAAgent: "idle",
  };
  for (const event of fired) {
    if (!(event.agent in base)) continue;
    if (event.event === "start") base[event.agent] = "running";
    else if (event.event === "complete") base[event.agent] = "done";
    else if (event.event === "blocker") base[event.agent] = "warn";
    else if (event.event === "resolved" && base[event.agent] !== "done") {
      base[event.agent] = "running";
    }
  }

  const blockerCount = fired.filter((e) => e.event === "blocker").length;
  const lastQa = [...fired].reverse().find((e) => e.agent === "QAAgent");
  const blockerActive = blockerCount > 0 && lastQa?.event === "blocker";

  return DEMO_PIPELINE.map((node) => {
    let status: AgentNodeStatus = base[node.agent];
    if (blockerActive && node.agent === "CollectorAgent") status = "retrying";
    if (blockerActive && node.agent === "QAAgent") status = "warn";
    return {
      agent: node.agent,
      label: node.label,
      role: node.role,
      status,
      retryCount: node.agent === "CollectorAgent" ? blockerCount : 0,
    };
  });
}

export default function DemoRunPage() {
  const router = useRouter();
  const headingRef = useRef<HTMLHeadingElement>(null);

  const [demoReplay, setDemoReplay] = useState(() => fallbackDemoReplayBundle());
  const [firedCount, setFiredCount] = useState(0);
  const [paused, setPaused] = useState(false);
  const startedAtRef = useRef<number | null>(null);
  const pausedAtRef = useRef<number | null>(null);
  const pausedAccumRef = useRef(0);
  const compressFactorRef = useRef(1);
  const demoTrace = demoReplay.trace;

  const totalDurationMs = demoTrace[demoTrace.length - 1]?.ts_offset_ms ?? 0;

  // Focus the heading on mount for screen readers.
  useEffect(() => {
    headingRef.current?.focus();
    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    compressFactorRef.current = reducedMotion ? COMPRESS_FACTOR_REDUCED : 1;
  }, []);

  useEffect(() => {
    let mounted = true;
    fetchDemoReplayBundle()
      .then((bundle) => {
        if (!mounted) return;
        startedAtRef.current = null;
        pausedAtRef.current = null;
        pausedAccumRef.current = 0;
        setFiredCount(0);
        setDemoReplay(bundle);
      })
      .catch(() => {
        // The local replay remains the offline-safe demo path.
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Drive the playback.
  useEffect(() => {
    let frame = 0;

    function tick(now: number) {
      if (startedAtRef.current === null) {
        startedAtRef.current = now;
      }
      if (paused) {
        if (pausedAtRef.current === null) pausedAtRef.current = now;
        frame = requestAnimationFrame(tick);
        return;
      }
      if (pausedAtRef.current !== null) {
        pausedAccumRef.current += now - pausedAtRef.current;
        pausedAtRef.current = null;
      }
      const elapsed =
        (now - startedAtRef.current - pausedAccumRef.current) /
        compressFactorRef.current;

      let nextFired = 0;
      for (const event of demoTrace) {
        if (event.ts_offset_ms <= elapsed) nextFired++;
        else break;
      }
      setFiredCount((prev) => (prev !== nextFired ? nextFired : prev));

      if (nextFired >= demoTrace.length) {
        // Linger 600ms to let the user see the final "QA pass" message.
        const lingerStart = now;
        function linger(t: number) {
          if (t - lingerStart >= 600) {
            router.push("/demo/report");
            return;
          }
          frame = requestAnimationFrame(linger);
        }
        frame = requestAnimationFrame(linger);
        return;
      }
      frame = requestAnimationFrame(tick);
    }

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [demoTrace, paused, router]);

  function handleSkip() {
    router.push("/demo/report");
  }

  const firedEvents = useMemo(() => demoTrace.slice(0, firedCount), [demoTrace, firedCount]);
  const visibleTrace = useMemo(
    () => firedEvents.slice(-12).reverse(),
    [firedEvents],
  );
  const demoNodes = useMemo(() => computeDemoNodes(firedEvents), [firedEvents]);

  const overallPct = totalDurationMs
    ? Math.min(
        100,
        Math.round(
          ((firedEvents[firedEvents.length - 1]?.ts_offset_ms ?? 0) /
            totalDurationMs) *
            100,
        ),
      )
    : 0;

  return (
    <>
      <DemoWatermark
        step={2}
        paused={paused}
        onPauseToggle={() => setPaused((p) => !p)}
        onSkip={handleSkip}
      />

      <PageContainer width="wide">
        <p
          className="mb-3 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          DEMO · Ch. 02 — DAG 回放
        </p>

        <h1
          ref={headingRef}
          tabIndex={-1}
          className={cn(
            "text-[1.7rem] leading-[1.05] sm:text-[clamp(2rem,3.6vw,2.6rem)]",
            "tracking-tight text-foreground mb-10",
            "outline-none focus-visible:outline-none",
            "animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)_both]",
          )}
          style={{
            fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
            fontWeight: 400,
            textWrap: "balance",
          }}
        >
          4 个 Agent 协作 · 反馈闭环可见
        </h1>

        <div className="grid gap-10 md:grid-cols-[1fr_360px]">
          {/* DAG nodes column */}
          <section aria-label="Agent 节点状态">
            <DagGraph nodes={demoNodes} />

            {/* Overall progress */}
            <div className="mt-8">
              <div className="flex items-baseline justify-between mb-2">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  整体进度
                </p>
                <p className="tabular text-[11px] text-muted-foreground">
                  {overallPct}% · {firedCount}/{demoTrace.length} 事件
                </p>
              </div>
              <div
                role="progressbar"
                aria-label="DAG 回放整体进度"
                aria-valuenow={overallPct}
                aria-valuemin={0}
                aria-valuemax={100}
                className="h-1 bg-border/60 overflow-hidden rounded-full"
              >
                <div
                  className="h-full bg-primary transition-[width] duration-150 ease-linear"
                  style={{ width: `${overallPct}%` }}
                />
              </div>
            </div>
          </section>

          {/* Trace events column */}
          <section
            aria-label="Trace 事件流"
            className="border border-border/60 rounded-md bg-card/60"
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/60">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                Trace
              </p>
              <p className="tabular text-[10px] text-muted-foreground/80">
                最近 {visibleTrace.length} 条
              </p>
            </div>
            <ul
              role="log"
              aria-live="polite"
              aria-label="Agent 事件实时流"
              className={cn(
                "max-h-[420px] overflow-y-auto px-4 py-3",
                "divide-y divide-border/40",
                "[&>li]:py-2",
              )}
            >
              {visibleTrace.length === 0 ? (
                <li className="py-2 text-[11px] text-muted-foreground/70">
                  等待 Collector 启动...
                </li>
              ) : (
                visibleTrace.map((event, idx) => (
                  <li
                    key={`${event.ts_offset_ms}-${idx}`}
                    className="animate-[fade-in_0.4s_ease-out_both]"
                  >
                    <div className="flex items-baseline gap-2 mb-0.5">
                      <span
                        className="tabular text-[10px] text-muted-foreground/80"
                        style={{ fontFamily: "var(--font-mono)" }}
                      >
                        {(event.ts_offset_ms / 1000).toFixed(1)}s
                      </span>
                      <span
                        className={cn(
                          "text-[10px] uppercase tracking-[0.15em]",
                          event.event === "blocker"
                            ? "text-destructive"
                            : event.event === "complete"
                              ? "text-primary"
                              : event.event === "resolved"
                                ? "text-[var(--color-accent-warm)]"
                                : "text-muted-foreground",
                        )}
                      >
                        {event.agent.replace("Agent", "")} · {event.event}
                      </span>
                    </div>
                    <p className="text-[12px] text-foreground/85 leading-snug">
                      {event.payload}
                    </p>
                  </li>
                ))
              )}
            </ul>
          </section>
        </div>
      </PageContainer>
    </>
  );
}

