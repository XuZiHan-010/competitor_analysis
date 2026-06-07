import type { TaskScopeContract } from "@/lib/mocks/types";
import { toBackendScopeContract } from "@/lib/api/scoping";
import { API_BASE_URL, apiFetch } from "@/lib/api/client";

export interface RunRecord {
  id: string;
  task_id: string;
  status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  retry_count: number;
  error_summary: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  competitors: string[];
}

export interface AgentTrace {
  id: string;
  task_run_id: string;
  agent_name: string;
  node_name: string;
  status: "started" | "succeeded" | "failed" | "skipped" | "retried";
  sequence_no: number;
  prompt: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  langsmith_run_id: string | null;
  decision_meta: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

export interface StreamEvent {
  id: number;
  run_id: string;
  event: string;
  data: Record<string, unknown>;
  created_at: string;
}

export async function startTaskRun(contract: TaskScopeContract): Promise<RunRecord> {
  const response = await apiFetch(`/api/tasks/${contract.task_id}/run`, {
    method: "POST",
    body: JSON.stringify({
      scope_contract: toBackendScopeContract(contract),
      force_feedback_demo: false,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to start task run: ${response.status}`);
  }

  return (await response.json()) as RunRecord;
}

export async function fetchRunRecord(runId: string): Promise<RunRecord> {
  const response = await apiFetch(`/api/tasks/${runId}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Failed to fetch run record: ${response.status}`);
  return (await response.json()) as RunRecord;
}

export async function fetchTaskTimeline(runId: string): Promise<AgentTrace[]> {
  const response = await apiFetch(`/api/tasks/${runId}/timeline`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch task timeline: ${response.status}`);
  }

  return (await response.json()) as AgentTrace[];
}

export function taskEventSource(runId: string): EventSource {
  return new EventSource(`${API_BASE_URL}/api/tasks/${runId}/events`, {
    withCredentials: true,
  });
}

export async function listTasks(limit = 50): Promise<RunRecord[]> {
  const res = await apiFetch(`/api/tasks?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`listTasks ${res.status}`);
  return res.json() as Promise<RunRecord[]>;
}

export async function deleteTask(runId: string): Promise<void> {
  const res = await apiFetch(`/api/tasks/${runId}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(`deleteTask ${res.status}`);
}
