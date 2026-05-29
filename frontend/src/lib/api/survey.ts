const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export type SurveyUploadKind = "questionnaire_result" | "interview_record";

export interface SurveyUploadResult {
  task_id: string;
  kind: SurveyUploadKind;
  parsed_evidence_count: number;
}

/**
 * Uploads first-party survey/interview text for a scope contract. Keyed by the
 * server-issued contract id (`TaskScopeContract.task_id`), so this must run
 * after `createScopingDraft` resolves — the parsed evidence is held server-side
 * and injected into the workflow when the task is started.
 */
export async function uploadSurveyEvidence(
  contractId: string,
  kind: SurveyUploadKind,
  content: string,
): Promise<SurveyUploadResult> {
  const res = await fetch(
    `${API_BASE_URL}/api/tasks/${contractId}/survey/upload`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, content }),
    },
  );
  if (!res.ok) throw new Error(`survey upload ${res.status}`);
  return (await res.json()) as SurveyUploadResult;
}
