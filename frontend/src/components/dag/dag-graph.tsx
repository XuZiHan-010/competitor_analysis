import { AgentNode } from "./agent-node";
import { FeedbackArc } from "./feedback-arc";
import type { DagNodeView } from "./types";

/**
 * Lays out the agent pipeline as a horizontal row of nodes with the QA→Collector
 * feedback arc beneath. Shared verbatim by `/tasks/[id]` (live) and `/demo/run`
 * (replay) so the two stay pixel-identical; callers only build `DagNodeView[]`.
 */
export function DagGraph({
  nodes,
  className,
}: {
  nodes: DagNodeView[];
  className?: string;
}) {
  // The arc appears once the loop has fired (a node carries retries or QA is
  // mid-blocker) and pulses while a blocker is actively being resolved.
  const arcVisible = nodes.some((n) => n.retryCount > 0 || n.status === "warn");
  const arcActive = nodes.some((n) => n.status === "warn" || n.status === "retrying");

  return (
    <div className={className}>
      <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {nodes.map((node, idx) => (
          <AgentNode
            key={node.agent}
            node={node}
            index={idx + 1}
            isLast={idx === nodes.length - 1}
          />
        ))}
      </ol>
      <FeedbackArc visible={arcVisible} active={arcActive} />
    </div>
  );
}
