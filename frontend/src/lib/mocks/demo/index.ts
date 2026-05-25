import type { TaskScopeContract } from "@/lib/mocks/types";
import scopeRaw from "./scope.json";
import traceRaw from "./trace.json";
import reportRaw from "./report.json";
import sourcesRaw from "./sources.json";
import type {
  DemoBundle,
  DemoReport,
  DemoSource,
  DemoTraceEvent,
} from "./types";

/**
 * Type-cast accessors for the fixture JSON. We rely on the TypeScript types in
 * `./types.ts` and trust the hand-authored JSON; if the backend ever generates
 * these from the real LangGraph run, a runtime validator (zod / valibot) can be
 * dropped in here without touching consumers.
 */
export const demoScope: TaskScopeContract = scopeRaw as unknown as TaskScopeContract;
export const demoTrace: DemoTraceEvent[] = traceRaw as DemoTraceEvent[];
export const demoReport: DemoReport = reportRaw as unknown as DemoReport;
export const demoSources: DemoSource[] = sourcesRaw as DemoSource[];

export const demoBundle: DemoBundle = {
  scope: demoScope,
  trace: demoTrace,
  report: demoReport,
  sources: demoSources,
};

/** Quick lookup helper used by the report page when rendering citation chips. */
export function getSourceById(id: string): DemoSource | undefined {
  return demoSources.find((s) => s.id === id);
}
