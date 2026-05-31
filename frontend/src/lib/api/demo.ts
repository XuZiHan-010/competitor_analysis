import { demoBundle } from "@/lib/mocks/demo";
import type { DemoBundle } from "@/lib/mocks/demo/types";
import { apiFetch } from "@/lib/api/client";

export interface DemoReplayBundle extends DemoBundle {
  demo_id: string;
  demo_mode: boolean;
  route_scope: "demo_only";
  source: string;
  export_formats: string[];
}

export async function fetchDemoReplayBundle(): Promise<DemoReplayBundle> {
  const response = await apiFetch("/api/demo/replay", {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch demo replay: ${response.status}`);
  }

  return (await response.json()) as DemoReplayBundle;
}

export function fallbackDemoReplayBundle(): DemoReplayBundle {
  return {
    ...demoBundle,
    demo_id: demoBundle.report.task_id,
    demo_mode: true,
    route_scope: "demo_only",
    source: "frontend_static_fixture",
    export_formats: ["markdown", "pdf", "pptx"],
  };
}
