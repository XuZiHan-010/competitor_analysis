import { cn } from "@/lib/utils";

/**
 * The Evaluator-Optimizer return path: when QA (rightmost node) raises a
 * blocker it 打回 Collector (leftmost node) for a re-run. Rendered as a dashed
 * orange track beneath the 4-node row, anchored at the 1st/4th column centers
 * (12.5% / 87.5%). Desktop-only — on narrow layouts nodes wrap and the per-node
 * "重跑 ×N" badge carries the same signal instead.
 *
 * The global prefers-reduced-motion reset (globals.css) neutralizes the pulse
 * while leaving the static dashed path fully visible.
 */
export function FeedbackArc({
  visible,
  active,
}: {
  /** Loop has fired at least once — render the track. */
  visible: boolean;
  /** A blocker is currently in flight — pulse the track. */
  active: boolean;
}) {
  if (!visible) return null;

  return (
    <>
      <span className="sr-only">
        QA 检测到 blocker，已将任务打回 Collector 重新采集。
      </span>
      <div
        aria-hidden="true"
        className={cn(
          "pointer-events-none relative mt-3 hidden h-9 lg:block",
          active && "motion-safe:animate-[thinking-pulse_1.6s_ease-in-out_infinite]",
        )}
      >
        {/* Stub dropping down out of QA (4th column center). */}
        <span className="absolute right-[12.5%] top-0 h-3 w-px bg-[var(--color-accent-warm)]/70" />
        {/* Horizontal dashed return track. */}
        <span className="absolute left-[12.5%] right-[12.5%] top-3 border-t-2 border-dashed border-[var(--color-accent-warm)]/70" />
        {/* Stub rising into Collector (1st column center) + upward arrowhead. */}
        <span className="absolute left-[12.5%] top-0 h-3 w-px bg-[var(--color-accent-warm)]/70" />
        <span
          className={cn(
            "absolute left-[12.5%] top-0 -translate-x-1/2 -translate-y-[3px]",
            "border-x-4 border-b-4 border-x-transparent",
            "border-b-[var(--color-accent-warm)]",
          )}
        />
        {/* Centered label sitting on the track. */}
        <span
          className={cn(
            "absolute left-1/2 top-3 -translate-x-1/2 -translate-y-1/2",
            "bg-background px-2 text-[10px] uppercase tracking-[0.16em]",
            "text-[var(--color-accent-warm)]",
          )}
          style={{ fontFamily: "var(--font-mono)" }}
        >
          ← 反馈打回 · 重采
        </span>
      </div>
    </>
  );
}
