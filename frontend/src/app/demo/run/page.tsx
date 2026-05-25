"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Check, Loader2 } from "lucide-react";
import { PageContainer } from "@/components/layout/page-container";
import { DemoWatermark } from "@/components/demo/demo-watermark";
import { demoTrace } from "@/lib/mocks/demo";
import type { DemoAgent, DemoNodeStatus, DemoTraceEvent } from "@/lib/mocks/demo/types";
import { cn } from "@/lib/utils";

const NODES: { agent: DemoAgent; label: string; role: string }[] = [
  { agent: "CollectorAgent", label: "Collector", role: "公开数据采集 + 溯源" },
  { agent: "AnalystAgent", label: "Analyst", role: "Schema 抽取 + 结构化" },
  { agent: "WriterAgent", label: "Writer", role: "章节渲染 + 摘要" },
  { agent: "QAAgent", label: "QA", role: "字段校验 + 反馈闭环" },
];

const COMPRESS_FACTOR_REDUCED = 0.2; // play at 5× when prefers-reduced-motion

function computeNodeStatuses(
  fired: DemoTraceEvent[],
): Record<DemoAgent, DemoNodeStatus> {
  const statuses: Record<DemoAgent, DemoNodeStatus> = {
    ScopingAgent: "idle",
    CollectorAgent: "idle",
    AnalystAgent: "idle",
    WriterAgent: "idle",
    QAAgent: "idle",
  };
  for (const event of fired) {
    if (event.event === "start") statuses[event.agent] = "running";
    else if (event.event === "complete") statuses[event.agent] = "ok";
    else if (event.event === "blocker") statuses[event.agent] = "warn";
    else if (event.event === "resolved" && statuses[event.agent] !== "ok") {
      statuses[event.agent] = "running";
    }
  }
  return statuses;
}

export default function DemoRunPage() {
  const router = useRouter();
  const headingRef = useRef<HTMLHeadingElement>(null);

  const [firedCount, setFiredCount] = useState(0);
  const [paused, setPaused] = useState(false);
  const startedAtRef = useRef<number | null>(null);
  const pausedAtRef = useRef<number | null>(null);
  const pausedAccumRef = useRef(0);
  const compressFactorRef = useRef(1);

  const totalDurationMs = demoTrace[demoTrace.length - 1]?.ts_offset_ms ?? 0;

  // Focus the heading on mount for screen readers.
  useEffect(() => {
    headingRef.current?.focus();
    const reducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    compressFactorRef.current = reducedMotion ? COMPRESS_FACTOR_REDUCED : 1;
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
  }, [paused, router]);

  function handleSkip() {
    router.push("/demo/report");
  }

  const firedEvents = useMemo(() => demoTrace.slice(0, firedCount), [firedCount]);
  const visibleTrace = useMemo(
    () => firedEvents.slice(-12).reverse(),
    [firedEvents],
  );
  const statuses = useMemo(() => computeNodeStatuses(firedEvents), [firedEvents]);

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
            <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {NODES.map((node, idx) => {
                const status = statuses[node.agent];
                return (
                  <li
                    key={node.agent}
                    aria-label={`${node.label} 状态：${
                      status === "ok"
                        ? "完成"
                        : status === "running"
                          ? "进行中"
                          : status === "warn"
                            ? "已打回"
                            : "等待"
                    }`}
                    className={cn(
                      "relative rounded-md border bg-card p-4",
                      "transition-colors duration-300",
                      status === "running" &&
                        "border-[var(--color-accent-warm)]/60 shadow-[0_0_0_3px_oklch(0.72_0.13_65_/_0.08)]",
                      status === "ok" && "border-primary/40",
                      status === "warn" && "border-destructive/50",
                      status === "idle" && "border-border/60 opacity-70",
                    )}
                  >
                    <div className="flex items-center gap-2.5 mb-2.5">
                      <NodeIcon status={status} />
                      <span
                        className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground tabular"
                        style={{ fontFamily: "var(--font-mono)" }}
                      >
                        0{idx + 1}
                      </span>
                    </div>
                    <p
                      className="text-base text-foreground/95"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {node.label}
                    </p>
                    <p className="text-[11px] text-muted-foreground/90 mt-1 leading-snug">
                      {node.role}
                    </p>

                    {/* Connector line - except after last node */}
                    {idx < NODES.length - 1 && (
                      <span
                        aria-hidden="true"
                        className={cn(
                          "hidden lg:block absolute top-1/2 -right-3 h-px w-6",
                          "bg-border",
                          status === "ok" && "bg-primary/50",
                        )}
                      />
                    )}
                  </li>
                );
              })}
            </ol>

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

function NodeIcon({ status }: { status: DemoNodeStatus }) {
  if (status === "ok") {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <Check className="h-3 w-3" />
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-accent-warm)] text-background motion-safe:animate-[thinking-pulse_1.4s_ease-in-out_infinite]">
        <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
      </span>
    );
  }
  if (status === "warn") {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-destructive/15 text-destructive">
        <AlertTriangle className="h-3 w-3" />
      </span>
    );
  }
  return (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-border/80 text-muted-foreground/60">
      <span className="block h-1 w-1 rounded-full bg-current" />
    </span>
  );
}
