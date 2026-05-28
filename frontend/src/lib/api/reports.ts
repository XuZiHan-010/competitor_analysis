import type { Lang } from "@/stores/lang-store";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function switchReportLanguage(taskId: string, language: Lang) {
  const response = await fetch(`${API_BASE_URL}/api/reports/${taskId}/language`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language }),
  });

  if (!response.ok) {
    throw new Error(`Failed to switch report language: ${response.status}`);
  }

  return response.json();
}
