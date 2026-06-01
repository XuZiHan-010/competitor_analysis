import { Activity, AlertTriangle, Loader2 } from "lucide-react";

export type ConnectionState = "connecting" | "open" | "closed";

/** SSE connection indicator for the live trace stream. */
export function ConnectionIcon({ state }: { state: ConnectionState }) {
  if (state === "open") return <Activity className="h-3.5 w-3.5 text-primary" />;
  if (state === "connecting")
    return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
  return <AlertTriangle className="h-3.5 w-3.5 text-destructive" />;
}
