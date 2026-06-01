import type { AgentTrace } from "@/lib/api/tasks";

/** One row in the live Agent timeline, summarizing a persisted trace. */
export function TraceRow({ trace }: { trace: AgentTrace }) {
  return (
    <li className="rounded-md border border-border/60 bg-card/50 px-4 py-3">
      <div className="mb-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span
          className="tabular text-[10px] uppercase tracking-[0.16em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          #{trace.sequence_no}
        </span>
        <span className="text-sm text-foreground">{trace.agent_name}</span>
        <span className="text-xs text-muted-foreground">
          {trace.node_name} / {trace.status}
        </span>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">
        {summarizeTrace(trace)}
      </p>
      <div className="mt-2 flex flex-wrap gap-3 text-[10px] uppercase tracking-[0.12em] text-muted-foreground/75">
        <span>{trace.latency_ms}ms</span>
        <span>{trace.tokens_in + trace.tokens_out} tokens</span>
        <span>${trace.cost_usd.toFixed(5)}</span>
      </div>
    </li>
  );
}

function summarizeTrace(trace: AgentTrace): string {
  const outputSummary = trace.output_payload.output_summary;
  const summary = trace.output_payload.summary;
  const error = trace.output_payload.error;
  if (typeof outputSummary === "string") return outputSummary;
  if (typeof summary === "string") return summary;
  if (typeof error === "string") return error;
  return JSON.stringify(trace.output_payload).slice(0, 220);
}
