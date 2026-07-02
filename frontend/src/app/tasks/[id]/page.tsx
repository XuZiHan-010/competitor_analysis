"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, ExternalLink } from "lucide-react";
import { PageContainer } from "@/components/layout/page-container";
import { DagGraph } from "@/components/dag/dag-graph";
import { TraceRow } from "@/components/dag/trace-row";
import { SurveyTraceGroup } from "@/components/dag/survey-trace-group";
import {
  ConnectionIcon,
  type ConnectionState,
} from "@/components/dag/connection-icon";
import type { AgentNodeStatus, DagNodeView } from "@/components/dag/types";
import {
  fetchTaskTimeline,
  fetchRunRecord,
  taskEventSource,
  type AgentTrace,
  type RunRecord,
  type StreamEvent,
} from "@/lib/api/tasks";
import { cn } from "@/lib/utils";

// Pipeline order matches the real LangGraph DAG: Collector → Analyst → QA → Writer.
// QA gates the structured analysis before Writer renders it; on a blocker QA loops
// back to Collector (the feedback arc beneath spans QA → Collector, with Writer
// sitting downstream outside the loop).
const PIPELINE: { agent: string; label: string; role: string }[] = [
  { agent: "CollectorAgent", label: "Collector", role: "公开数据采集 + 溯源" },
  { agent: "AnalystAgent", label: "Analyst", role: "Schema 抽取 + 结构化" },
  { agent: "QAAgent", label: "QA", role: "字段校验 + 反馈闭环" },
  { agent: "WriterAgent", label: "Writer", role: "章节渲染 + 摘要" },
];
const AGENT_ORDER = PIPELINE.map((node) => node.agent);
type RunStatus = RunRecord["status"];

const STREAM_EVENT_NAMES = [
  "run.started",
  "node.started",
  "node.succeeded",
  "node.failed",
  "collector.degraded",
  "qa.blocker",
  "run.succeeded",
  "run.failed",
  "stream.error",
];

export default function TaskRunPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [traces, setTraces] = useState<AgentTrace[]>([]);
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [streamWarning, setStreamWarning] = useState<string | null>(null);
  const [reportTaskId, setReportTaskId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [finalizingWarningRunId, setFinalizingWarningRunId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    let terminal = false;
    const source = taskEventSource(runId);

    async function refreshTimeline() {
      try {
        const [next, run] = await Promise.all([
          fetchTaskTimeline(runId),
          fetchRunRecord(runId),
        ]);
        if (!mounted) return;
        setTraces(next);
        setRunStatus(run.status);
        if (run.status === "succeeded" && run.task_id) {
          setReportTaskId(run.task_id);
          setError(null);
          setStreamWarning(null);
          terminal = true;
          source.close();
          setConnectionState("closed");
        }
        if (run.status === "failed") {
          setError(formatRunFailure(run.error_summary));
          setStreamWarning(null);
          terminal = true;
          source.close();
          setConnectionState("closed");
        }
      } catch {
        // silently ignore — the empty-state "等待第一条 trace 写入..." handles this
      }
    }

    function appendEvent(message: Event) {
      const event = parseStreamEvent((message as MessageEvent<string>).data);
      if (!event || !mounted) return;

      setEvents((current) => [...current, event].slice(-40));
      if (event.event === "run.succeeded") {
        setRunStatus("succeeded");
        // Do not set reportTaskId directly from the SSE payload — let refreshTimeline
        // confirm the report is readable via the server before showing the button.
        void refreshTimeline();
        terminal = true;
        window.clearInterval(interval);
        source.close();
        setConnectionState("closed");
      }
      if (event.event === "node.succeeded" || event.event === "node.failed") {
        void refreshTimeline();
      }
      if (event.event === "run.failed") {
        setRunStatus("failed");
        setError(formatRunFailure(event.data));
        setStreamWarning(null);
        void refreshTimeline();
        terminal = true;
        window.clearInterval(interval);
        source.close();
        setConnectionState("closed");
      }
      if (event.event === "stream.error") {
        setStreamWarning(formatStreamWarning(event.data));
        source.close();
        setConnectionState("closed");
      }
    }

    void refreshTimeline();
    const interval = window.setInterval(refreshTimeline, 1500);

    source.onopen = () => {
      if (!mounted) return;
      setConnectionState("open");
      setStreamWarning(null);
    };
    source.onerror = () => {
      if (!mounted) return;
      setConnectionState("closed");
      if (terminal) source.close();
    };
    STREAM_EVENT_NAMES.forEach((eventName) => {
      source.addEventListener(eventName, appendEvent);
    });

    return () => {
      mounted = false;
      window.clearInterval(interval);
      source.close();
    };
  }, [runId]);

  const nodes = useMemo(() => computeDagNodes(traces, events), [events, traces]);
  const sortedTraces = useMemo(
    () => [...traces].sort((a, b) => a.sequence_no - b.sequence_no),
    [traces],
  );
  // SurveyTool runs as a sub-workflow inside Collector and emits 7 stages ×
  // N competitors; fold each consecutive run of its traces into one collapsible
  // group so the four top-level agents stay legible in the flat timeline.
  const timelineItems = useMemo(
    () => groupTimelineItems(sortedTraces),
    [sortedTraces],
  );
  const latestEvents = [...events].reverse().slice(0, 8);
  const doneCount = nodes.filter((node) => node.status === "done").length;
  const allNodesDone = doneCount === nodes.length;
  const terminalSucceeded = Boolean(reportTaskId) || runStatus === "succeeded";
  const terminalFailed = Boolean(error) || runStatus === "failed";
  const rawOverallPct = Math.round((doneCount / nodes.length) * 100);
  const overallPct = terminalSucceeded
    ? 100
    : allNodesDone && !terminalFailed
      ? 99
      : rawOverallPct;
  const progressLabel = terminalSucceeded
    ? "报告已生成"
    : allNodesDone && !terminalFailed
      ? "正在保存报告"
      : "Overall";

  useEffect(() => {
    if (!allNodesDone || terminalSucceeded || terminalFailed) return;
    const timeout = window.setTimeout(() => setFinalizingWarningRunId(runId), 120000);
    return () => window.clearTimeout(timeout);
  }, [allNodesDone, runId, terminalSucceeded, terminalFailed]);

  return (
    <PageContainer width="wide">
      <header className="mb-8">
        <p
          className="mb-3 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          Live DAG / Run {runId.slice(0, 8)}
        </p>
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <h1
              className="text-[2rem] leading-[1.05] tracking-tight text-foreground sm:text-[clamp(2.35rem,5vw,3.2rem)]"
              style={{
                fontFamily: "var(--font-display)",
                fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
                fontWeight: 400,
                textWrap: "balance",
              }}
            >
              Agent 协作正在运行
            </h1>
            <p className="mt-3 max-w-[58ch] text-sm leading-relaxed text-muted-foreground">
              后端 LangGraph 正在按 Collector、Analyst、QA、Writer 顺序推进；
              QA 发现 blocker 时会在事件流中显示打回与补采信号。
            </p>
          </div>

          {reportTaskId && (
            <Link
              href={`/reports/${reportTaskId}`}
              className={cn(
                "inline-flex h-9 items-center justify-center gap-2 rounded-lg",
                "bg-primary px-3 text-sm font-medium text-primary-foreground",
                "transition-colors hover:bg-primary/90 focus-visible:outline-none",
                "focus-visible:ring-3 focus-visible:ring-ring/50",
              )}
            >
              查看报告
              <ExternalLink className="h-4 w-4" />
            </Link>
          )}
        </div>
      </header>

      <section className="mb-8">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            {progressLabel}
          </span>
          <span className="tabular text-xs text-muted-foreground">{overallPct}%</span>
        </div>
        <div
          role="progressbar"
          aria-label="任务运行整体进度"
          aria-valuenow={overallPct}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-1 rounded-full bg-border/70"
        >
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-500"
            style={{ width: `${overallPct}%` }}
          />
        </div>
      </section>

      {error && (
        <div
          role="alert"
          aria-live="polite"
          className="mb-6 flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          {error}
        </div>
      )}

      {streamWarning && !error && (
        <div
          role="status"
          aria-live="polite"
          className="mb-6 flex items-center gap-2 rounded-md border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200"
        >
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          {streamWarning}
        </div>
      )}

      {finalizingWarningRunId === runId &&
        allNodesDone &&
        !terminalSucceeded &&
        !terminalFailed &&
        !error &&
        !streamWarning && (
          <div
            role="status"
            aria-live="polite"
            className="mb-6 flex items-center gap-2 rounded-md border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200"
          >
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            报告已生成，后端正在收尾保存；若长时间停留，请重新发起本次分析。
          </div>
        )}

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <section aria-label="Agent 节点状态">
          <DagGraph nodes={nodes} />

          <section className="mt-8" aria-labelledby="timeline-title">
            <div className="mb-3 flex items-baseline justify-between">
              <h2
                id="timeline-title"
                className="text-lg text-foreground"
                style={{ fontFamily: "var(--font-display)", fontWeight: 500 }}
              >
                Agent Timeline
              </h2>
              <span className="tabular text-xs text-muted-foreground">
                {sortedTraces.length} traces
              </span>
            </div>

            <ol className="space-y-2">
              {sortedTraces.length === 0 ? (
                <li className="rounded-md border border-border/60 bg-card/50 px-4 py-4 text-sm text-muted-foreground">
                  等待第一条 trace 写入...
                </li>
              ) : (
                timelineItems.map((item) =>
                  item.kind === "survey-group" ? (
                    <SurveyTraceGroup key={item.key} traces={item.traces} />
                  ) : (
                    <TraceRow key={item.trace.id} trace={item.trace} />
                  ),
                )
              )}
            </ol>
          </section>
        </section>

        <aside
          aria-label="SSE 事件流"
          className="rounded-md border border-border/60 bg-card/60"
        >
          <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
            <div className="flex items-center gap-2">
              <ConnectionIcon state={connectionState} />
              <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                SSE
              </span>
            </div>
            <span className="tabular text-[10px] text-muted-foreground">
              {connectionState}
            </span>
          </div>
          <ul className="max-h-[460px] divide-y divide-border/40 overflow-y-auto px-4 py-2">
            {latestEvents.length === 0 ? (
              <li className="py-3 text-xs text-muted-foreground">等待事件...</li>
            ) : (
              latestEvents.map((event, index) => (
                <li key={`${event.id}-${event.event}-${index}`} className="py-3">
                  <div className="mb-1 flex items-baseline gap-2">
                    <span
                      className="tabular text-[10px] text-muted-foreground"
                      style={{ fontFamily: "var(--font-mono)" }}
                    >
                      #{event.id}
                    </span>
                    <span className="text-[11px] uppercase tracking-[0.14em] text-foreground/80">
                      {event.event}
                    </span>
                  </div>
                  <p className="break-words text-xs leading-relaxed text-muted-foreground">
                    {summarizeEventData(event.data)}
                  </p>
                </li>
              ))
            )}
          </ul>
        </aside>
      </div>
    </PageContainer>
  );
}

type TimelineItem =
  | { kind: "trace"; trace: AgentTrace }
  | { kind: "survey-group"; key: string; traces: AgentTrace[] };

/**
 * Collapses each consecutive run of SurveyTool traces into a single group while
 * leaving the four top-level agents as standalone rows. Traces are assumed
 * pre-sorted by sequence_no.
 */
function groupTimelineItems(traces: AgentTrace[]): TimelineItem[] {
  const items: TimelineItem[] = [];
  let group: AgentTrace[] = [];

  const flush = () => {
    if (group.length === 0) return;
    items.push({
      kind: "survey-group",
      key: `survey-${group[0].id}`,
      traces: group,
    });
    group = [];
  };

  for (const trace of traces) {
    if (trace.agent_name === "SurveyTool") {
      group.push(trace);
      continue;
    }
    flush();
    items.push({ kind: "trace", trace });
  }
  flush();
  return items;
}

/**
 * Derives the DAG view model from persisted traces + live SSE events.
 * Each QA blocker means Collector re-ran, so while a blocker is unresolved we
 * surface QA as `warn` and Collector as `retrying` with a "重跑 ×N" badge.
 */
function computeDagNodes(
  traces: AgentTrace[],
  events: StreamEvent[],
): DagNodeView[] {
  const statuses: Record<string, AgentNodeStatus> = Object.fromEntries(
    AGENT_ORDER.map((agent) => [agent, "idle" as AgentNodeStatus]),
  );
  const retriedTraceCounts: Record<string, number> = {};

  for (const trace of [...traces].sort((a, b) => a.sequence_no - b.sequence_no)) {
    if (trace.status === "failed") {
      statuses[trace.agent_name] = "failed";
    } else if (trace.status === "retried") {
      statuses[trace.agent_name] = "done";
      retriedTraceCounts[trace.agent_name] =
        (retriedTraceCounts[trace.agent_name] ?? 0) + 1;
    } else {
      statuses[trace.agent_name] = "done";
    }
  }

  const activeStartedAgents = new Set<string>();
  for (const event of events) {
    const agentName = event.data.agent_name;
    if (typeof agentName !== "string") continue;
    if (event.event === "node.started") {
      activeStartedAgents.add(agentName);
    } else if (
      event.event === "node.succeeded" ||
      event.event === "node.failed"
    ) {
      activeStartedAgents.delete(agentName);
    }
  }

  const runSucceeded = events.some((e) => e.event === "run.succeeded");
  const runFailed = events.some((e) => e.event === "run.failed");
  const qaBlockerCount = events.filter((e) => e.event === "qa.blocker").length;
  const blockerActive = qaBlockerCount > 0 && !runSucceeded && !runFailed;

  if (runFailed) {
    const lastTrace = [...traces].sort((a, b) => b.sequence_no - a.sequence_no)[0];
    if (lastTrace) statuses[lastTrace.agent_name] = "failed";
  } else if (!runSucceeded) {
    const runningAgents = AGENT_ORDER.filter(
      (agent) =>
        statuses[agent] === "idle" && activeStartedAgents.has(agent),
    );
    if (runningAgents.length > 0) {
      for (const agent of runningAgents) statuses[agent] = "running";
    } else {
      const firstIdle = AGENT_ORDER.find((agent) => statuses[agent] === "idle");
      if (firstIdle) statuses[firstIdle] = "running";
    }
  }

  if (blockerActive) {
    statuses.QAAgent = "warn";
    statuses.CollectorAgent = "retrying";
  }

  const collectorRetries = Math.max(
    qaBlockerCount,
    retriedTraceCounts.CollectorAgent ?? 0,
  );

  return PIPELINE.map((node) => ({
    agent: node.agent,
    label: node.label,
    role: node.role,
    status: statuses[node.agent],
    retryCount: node.agent === "CollectorAgent" ? collectorRetries : 0,
  }));
}

function parseStreamEvent(data: string): StreamEvent | null {
  try {
    return JSON.parse(data) as StreamEvent;
  } catch {
    return null;
  }
}

function formatRunFailure(errorSummary: Record<string, unknown> | null): string {
  const message = errorSummary?.message;
  const exceptionClass = errorSummary?.exception_class;
  if (typeof message === "string" && message) {
    if (typeof exceptionClass === "string" && exceptionClass) {
      return `任务运行失败：${exceptionClass} - ${message}`;
    }
    return `任务运行失败：${message}`;
  }
  if (typeof exceptionClass === "string" && exceptionClass) {
    return `任务运行失败：${exceptionClass}`;
  }
  return "任务运行失败，请查看后端日志或重试。";
}

function formatStreamWarning(data: Record<string, unknown>): string {
  const message = data.message;
  if (typeof message === "string" && message) return message;
  return "事件流连接中断，任务仍可能在后台运行；页面将继续刷新任务状态。";
}

function summarizeEventData(data: Record<string, unknown>): string {
  const taskId = data.task_id;
  const reportId = data.report_id;
  const message = data.message;
  const issues = data.issues;
  const outputPayload = data.output_payload;
  const outputSummary =
    outputPayload &&
    typeof outputPayload === "object" &&
    "output_summary" in outputPayload
      ? (outputPayload as Record<string, unknown>).output_summary
      : null;
  const agentName = data.agent_name;
  const nodeName = data.node_name;
  const status = data.status;
  if (typeof message === "string") return message;
  if (typeof outputSummary === "string" && outputSummary) return outputSummary;
  if (typeof agentName === "string" && typeof nodeName === "string") {
    return `${agentName} / ${nodeName}${typeof status === "string" ? ` / ${status}` : ""}`;
  }
  if (typeof reportId === "string" && reportId) return `report ${reportId}`;
  if (typeof taskId === "string" && taskId) return `task ${taskId}`;
  if (Array.isArray(issues)) return `${issues.length} QA issue(s)`;
  return JSON.stringify(data);
}
