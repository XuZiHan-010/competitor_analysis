import { AlertTriangle, Check, Loader2, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentNodeStatus, DagNodeView } from "./types";

const STATUS_ARIA: Record<AgentNodeStatus, string> = {
  idle: "等待",
  running: "进行中",
  done: "完成",
  failed: "失败",
  warn: "已打回",
  retrying: "重跑中",
};

export function AgentNode({
  node,
  index,
  isLast,
}: {
  node: DagNodeView;
  /** 1-based position in the pipeline, rendered as a 0N serial. */
  index: number;
  isLast: boolean;
}) {
  const { label, role, status, retryCount } = node;

  return (
    <li
      aria-label={`${label} 状态：${STATUS_ARIA[status]}`}
      className={cn(
        "relative rounded-md border bg-card p-4 transition-colors duration-300",
        status === "running" &&
          "border-[var(--color-accent-warm)]/60 shadow-[0_0_0_3px_oklch(0.72_0.13_65_/_0.08)]",
        status === "retrying" &&
          "border-[var(--color-accent-warm)]/70 shadow-[0_0_0_3px_oklch(0.72_0.13_65_/_0.10)]",
        status === "done" && "border-primary/40",
        status === "warn" && "border-destructive/50",
        status === "failed" && "border-destructive/60",
        status === "idle" && "border-border/60 opacity-70",
      )}
    >
      <div className="mb-2.5 flex items-center justify-between gap-2">
        <NodeIcon status={status} />
        <span
          className="tabular text-[10px] uppercase tracking-[0.18em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {String(index).padStart(2, "0")}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <p
          className="text-base text-foreground/95"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {label}
        </p>
        {retryCount > 0 && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5",
              "bg-[var(--color-accent-warm)]/15 text-[var(--color-accent-warm)]",
              "text-[10px] font-medium tabular",
            )}
            title={`经反馈闭环重跑 ${retryCount} 次`}
          >
            <RotateCcw className="h-2.5 w-2.5" />
            重跑 ×{retryCount}
          </span>
        )}
      </div>
      <p className="mt-1 text-[11px] leading-snug text-muted-foreground/90">{role}</p>

      {/* Forward connector to the next node — desktop only. */}
      {!isLast && (
        <span
          aria-hidden="true"
          className={cn(
            "absolute top-1/2 -right-3 hidden h-px w-6 bg-border lg:block",
            (status === "done" || status === "retrying") && "bg-primary/50",
          )}
        />
      )}
    </li>
  );
}

function NodeIcon({ status }: { status: AgentNodeStatus }) {
  if (status === "done") {
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
  if (status === "retrying") {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-accent-warm)] text-background motion-safe:animate-[thinking-pulse_1.4s_ease-in-out_infinite]">
        <RotateCcw className="h-3 w-3 motion-safe:animate-spin" />
      </span>
    );
  }
  if (status === "warn" || status === "failed") {
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
