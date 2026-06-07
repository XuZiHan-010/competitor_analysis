"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageContainer } from "@/components/layout/page-container";
import { deleteTask, listTasks, type RunRecord } from "@/lib/api/tasks";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<
  RunRecord["status"],
  { label: string; tone: string }
> = {
  pending: {
    label: "等待中",
    tone: "text-muted-foreground border-border/60 bg-transparent",
  },
  running: {
    label: "运行中",
    tone: "text-primary border-primary/40 bg-primary/8",
  },
  succeeded: {
    label: "已完成",
    tone: "text-[oklch(0.62_0.17_145)] border-[oklch(0.62_0.17_145)]/30 bg-[oklch(0.62_0.17_145)]/8",
  },
  failed: {
    label: "失败",
    tone: "text-destructive border-destructive/30 bg-destructive/8",
  },
  cancelled: {
    label: "已取消",
    tone: "text-muted-foreground/60 border-border/40 bg-transparent",
  },
};

export default function TasksPage() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTasks()
      .then((data) => { setRuns(data); setLoading(false); })
      .catch(() => { setError("任务列表加载失败"); setLoading(false); });
  }, []);

  const handleDelete = useCallback(async (runId: string) => {
    const previous = runs;
    setRuns((prev) => prev.filter((r) => r.id !== runId)); // optimistic
    try {
      await deleteTask(runId);
      toast.success("任务已删除");
    } catch {
      setRuns(previous); // rollback
      toast.error("删除失败，请重试");
    }
  }, [runs]);

  return (
    <PageContainer>
      {/* Header */}
      <header className="mb-10">
        <p
          className="mb-3 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          竞品分析 · 历史任务
        </p>
        <div className="flex items-end justify-between gap-4">
          <h1
            className="text-[2.4rem] leading-[1.05] tracking-tight text-foreground"
            style={{
              fontFamily: "var(--font-display)",
              fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
              fontWeight: 380,
              textWrap: "balance",
            }}
          >
            任务列表
          </h1>
          <Link
            href="/tasks/new"
            className={cn(
              "inline-flex items-center gap-1.5 shrink-0",
              "text-[11px] uppercase tracking-[0.14em] px-3.5 py-2 rounded",
              "bg-primary text-primary-foreground hover:bg-primary/90 transition-colors",
            )}
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <Plus className="h-3.5 w-3.5" />
            新建任务
          </Link>
        </div>
        <div className="rule-fade mt-8" aria-hidden="true" />
      </header>

      {/* Column headers */}
      {!loading && !error && runs.length > 0 && (
        <div
          className="grid grid-cols-[minmax(0,1fr)_76px_104px_auto] gap-3 px-4 pb-2 text-[10px] uppercase tracking-[0.18em] text-muted-foreground/60 sm:grid-cols-[minmax(180px,1fr)_90px_140px_minmax(180px,auto)] sm:gap-4 sm:px-5"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          <span>Competitors</span>
          <span>状态</span>
          <span>开始时间</span>
          <span className="text-right">操作</span>
        </div>
      )}

      {loading ? (
        <TasksSkeleton />
      ) : error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : runs.length === 0 ? (
        <EmptyState />
      ) : (
        <ol className="space-y-1.5" aria-label="任务列表">
          {runs.map((run) => (
            <TaskRow key={run.id} run={run} onDelete={handleDelete} />
          ))}
        </ol>
      )}
    </PageContainer>
  );
}

function TaskRow({
  run,
  onDelete,
}: {
  run: RunRecord;
  onDelete: (runId: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const cfg = STATUS_CONFIG[run.status];
  const competitors = run.competitors.filter((name) => name.trim());
  const competitorLabel = competitors.length > 0 ? competitors.join(" / ") : run.task_id.slice(0, 8);
  const dateStr = run.started_at
    ? new Date(run.started_at).toLocaleString("zh-CN", {
        dateStyle: "short",
        timeStyle: "short",
      })
    : "—";

  return (
    <li className="rounded-md border border-border/60 bg-card/40 hover:bg-card/70 transition-colors">
      <div className="grid grid-cols-[minmax(0,1fr)_76px_104px_auto] items-center gap-3 px-4 py-3.5 sm:grid-cols-[minmax(180px,1fr)_90px_140px_minmax(180px,auto)] sm:gap-4 sm:px-5">
        {/* Competitors */}
        <div className="min-w-0">
          <p
            className="truncate text-[13px] leading-tight text-foreground"
            title={competitorLabel}
            translate="no"
          >
            {competitorLabel}
          </p>
          <span
            className="tabular text-[10px] text-muted-foreground/50"
            style={{ fontFamily: "var(--font-mono)" }}
            title={run.task_id}
          >
            {run.task_id.slice(0, 8)}
          </span>
        </div>

        {/* Status badge */}
        <span
          className={cn(
            "inline-flex items-center text-[10px] uppercase tracking-[0.12em]",
            "px-1.5 py-0.5 rounded border w-fit",
            cfg.tone,
          )}
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {cfg.label}
        </span>

        {/* Date */}
        <span
          className="tabular text-[12px] text-muted-foreground/70"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {dateStr}
        </span>

        {/* Action links */}
        <div className="flex items-center justify-end gap-4">
          <Link
            href={`/tasks/${run.id}`}
            className={cn(
              "inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.12em]",
              "text-muted-foreground hover:text-foreground transition-colors",
            )}
            style={{ fontFamily: "var(--font-mono)" }}
          >
            DAG <ArrowRight className="h-3 w-3" />
          </Link>

          {run.status === "succeeded" && (
            <Link
              href={`/reports/${run.task_id}`}
              className={cn(
                "inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.12em]",
                "text-primary hover:text-primary/80 transition-colors",
              )}
              style={{ fontFamily: "var(--font-mono)" }}
            >
              报告 <ArrowRight className="h-3 w-3" />
            </Link>
          )}

          {confirming ? (
            <div
              role="group"
              aria-label="确认删除任务"
              className="flex items-center gap-2.5 text-[11px] uppercase tracking-[0.12em]"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              <span className="text-muted-foreground/70">确认删除?</span>
              <button
                type="button"
                onClick={() => {
                  setConfirming(false);
                  onDelete(run.id);
                }}
                className={cn(
                  "rounded px-1 text-destructive hover:text-destructive/80 transition-colors",
                  "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-destructive/50",
                  "[touch-action:manipulation]",
                )}
              >
                删除
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className={cn(
                  "rounded px-1 text-muted-foreground hover:text-foreground transition-colors",
                  "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border",
                  "[touch-action:manipulation]",
                )}
              >
                取消
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              aria-label="删除任务"
              className={cn(
                "inline-flex items-center justify-center rounded p-1",
                "text-muted-foreground/40 hover:text-destructive transition-colors",
                "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-destructive/50",
                "[touch-action:manipulation]",
              )}
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
    </li>
  );
}

function EmptyState() {
  return (
    <div className="rounded-md border border-dashed border-border/60 py-20 flex flex-col items-center gap-5">
      <p
        className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground/70"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        还没有分析任务
      </p>
      <Link
        href="/tasks/new"
        className={cn(
          "inline-flex items-center gap-2",
          "text-[11px] uppercase tracking-[0.14em] px-4 py-2 rounded",
          "border border-border/70 text-foreground/70 hover:text-foreground hover:border-border",
          "transition-colors",
        )}
        style={{ fontFamily: "var(--font-mono)" }}
      >
        <Plus className="h-3.5 w-3.5" />
        创建第一个任务
      </Link>
    </div>
  );
}

function TasksSkeleton() {
  return (
    <div className="space-y-1.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-[52px] rounded-md border border-border/60 bg-card/40 animate-pulse"
          style={{ opacity: 1 - i * 0.15 }}
        />
      ))}
    </div>
  );
}
