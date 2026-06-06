// Resolves a LangSmith URL for a persisted trace's run id.
//
// A deep link to a specific run requires the org + project UUIDs, which the
// frontend does not have — only the run id and project name. So the exact run
// URL is supplied via an optional env template (with a `{run_id}` placeholder,
// e.g. https://smith.langchain.com/o/<org>/projects/p/<proj>/r/{run_id}). When
// it is unset we fall back to the LangSmith dashboard; the full run id is still
// surfaced in the link's tooltip/label as proof of trace linkage.
const RUN_URL_TEMPLATE = process.env.NEXT_PUBLIC_LANGSMITH_RUN_URL;
const DASHBOARD_URL = "https://smith.langchain.com";

export function langsmithRunUrl(runId: string): string {
  if (RUN_URL_TEMPLATE && RUN_URL_TEMPLATE.includes("{run_id}")) {
    return RUN_URL_TEMPLATE.replace("{run_id}", encodeURIComponent(runId));
  }
  return DASHBOARD_URL;
}

// Project-level entry for surfaces that have no specific run id (e.g. the report
// page). Prefers an explicit project URL, else the run template's origin, else
// the dashboard root — always returns something clickable.
const PROJECT_URL = process.env.NEXT_PUBLIC_LANGSMITH_PROJECT_URL;

export function langsmithProjectUrl(): string {
  if (PROJECT_URL) return PROJECT_URL;
  if (RUN_URL_TEMPLATE) {
    try {
      return new URL(RUN_URL_TEMPLATE).origin;
    } catch {
      // malformed template — fall through to dashboard
    }
  }
  return DASHBOARD_URL;
}
