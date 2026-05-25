"use client";

import { useRouter } from "next/navigation";
import { Pause, Play, SkipForward, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useScopingStore } from "@/stores/scoping-store";

interface DemoWatermarkProps {
  /** 1-indexed step in the playback (1 = scoping, 2 = run, 3 = report). */
  step: 1 | 2 | 3;
  /** Total demo steps; kept as a prop so future demo arcs can extend it. */
  totalSteps?: number;
  /** Whether the host page's auto-advance timer is paused. */
  paused?: boolean;
  /** Called when the user toggles the pause / play control. */
  onPauseToggle?: () => void;
  /** Called when the user wants to skip the current step's auto-advance. */
  onSkip?: () => void;
}

/**
 * Fixed top-right pill badge present on every `/demo/*` page.
 *
 * Design notes (PRD §十一Q.2):
 * - Editorial italic "演示样例" label + monospace step counter (01/03)
 * - Pulsing ochre dot signals "live playback"
 * - Always-on-top, but `pointer-events: none` on the decorative shell;
 *   only the controls accept pointer input. Lets users select text under it.
 * - Honors safe-area on notched devices.
 */
export function DemoWatermark({
  step,
  totalSteps = 3,
  paused = false,
  onPauseToggle,
  onSkip,
}: DemoWatermarkProps) {
  const router = useRouter();
  const exitDemoMode = useScopingStore((s) => s.exitDemoMode);

  const stepLabel = `${String(step).padStart(2, "0")} / ${String(totalSteps).padStart(2, "0")}`;

  function handleExit() {
    exitDemoMode();
    router.push("/tasks/new");
  }

  return (
    <div
      // The outer wrapper covers an area but doesn't capture pointer events.
      // Each interactive child re-enables pointer-events: auto.
      className={cn(
        // Sit just below the sticky TopNav (h-14 / 3.5rem) so the language /
        // theme toggles stay reachable in the corner.
        "pointer-events-none fixed right-0 top-14 z-50",
        "p-3 sm:p-4",
        "pr-[max(0.75rem,env(safe-area-inset-right))]",
      )}
      aria-hidden={false}
    >
      <div
        role="region"
        aria-label="演示回放控制"
        className={cn(
          "pointer-events-auto flex items-center gap-3",
          "rounded-full border border-border/70 bg-card/85",
          "px-3.5 py-1.5",
          "shadow-[0_6px_24px_-12px_oklch(0.18_0.012_245_/_0.25)]",
          "backdrop-blur-md backdrop-saturate-150",
          "animate-[fade-in_0.6s_ease-out_both]",
        )}
      >
        {/* Pulse dot */}
        <span
          aria-hidden="true"
          className={cn(
            "relative inline-flex h-1.5 w-1.5 shrink-0 rounded-full",
            "bg-[var(--color-accent-warm)]",
          )}
        >
          {!paused && (
            <span
              className={cn(
                "absolute inset-0 rounded-full",
                "bg-[var(--color-accent-warm)]/60",
                "motion-safe:animate-ping",
              )}
            />
          )}
        </span>

        {/* Italic label */}
        <span
          className="hidden sm:inline text-[11px] italic text-foreground/85 tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          演示样例
        </span>

        {/* Step counter — tabular-nums for stable width */}
        <span
          className="tabular text-[11px] uppercase tracking-[0.16em] text-muted-foreground"
          aria-label={`步骤 ${step} / ${totalSteps}`}
        >
          {stepLabel}
        </span>

        <span aria-hidden="true" className="h-3 w-px bg-border/80" />

        {/* Controls */}
        {onPauseToggle ? (
          <button
            type="button"
            onClick={onPauseToggle}
            aria-label={paused ? "继续自动播放" : "暂停自动播放"}
            aria-pressed={paused}
            className={cn(
              "inline-flex h-6 w-6 items-center justify-center rounded-full",
              "text-muted-foreground hover:text-foreground",
              "hover:bg-secondary/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              "transition-colors",
            )}
          >
            {paused ? <Play className="h-3 w-3" /> : <Pause className="h-3 w-3" />}
          </button>
        ) : null}

        {onSkip ? (
          <button
            type="button"
            onClick={onSkip}
            aria-label="跳到下一个演示页面"
            className={cn(
              "inline-flex h-6 w-6 items-center justify-center rounded-full",
              "text-muted-foreground hover:text-foreground",
              "hover:bg-secondary/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              "transition-colors",
            )}
          >
            <SkipForward className="h-3 w-3" />
          </button>
        ) : null}

        <button
          type="button"
          onClick={handleExit}
          aria-label="退出演示，返回真实任务页"
          className={cn(
            "inline-flex h-6 items-center gap-1 rounded-full px-2",
            "text-[10px] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground",
            "hover:bg-secondary/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            "transition-colors",
          )}
        >
          <X className="h-3 w-3" />
          <span className="hidden sm:inline">退出</span>
        </button>
      </div>

      {/* Caption ribbon under the pill — printed underneath for context */}
      <p
        className={cn(
          "pointer-events-none mt-1.5 max-w-[280px] text-right",
          "text-[10px] leading-snug text-muted-foreground/80",
        )}
      >
        本路径为预录回放（PRD §十一Q）。若需真实任务请点「退出」。
      </p>
    </div>
  );
}
