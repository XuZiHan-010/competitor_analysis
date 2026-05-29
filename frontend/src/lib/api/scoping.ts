import type {
  ClarifyingQuestion,
  DimensionSpec,
  TaskScopeContract,
  UserResearchPlan,
} from "@/lib/mocks/types";
import { emptyUserResearchPlan } from "@/lib/mocks/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

interface BackendCompetitorCandidate {
  name: string;
  source: "user_chip" | "nl_extracted" | "ai_recommended";
  rationale?: string | null;
}

interface BackendScopeDimension {
  id: string;
  title: string;
  intent: string;
  layer: "core" | "extension";
  order: number;
  enabled: boolean;
  locked: boolean;
  source: "system" | "ai_suggested" | "user_added";
  schema_ref?: string | null;
}

interface BackendTaskScopeContract {
  id: string;
  user_brief: string;
  intent_mode: "list" | "intent" | "mixed";
  target_product?: string | null;
  competitors: BackendCompetitorCandidate[];
  clarifications: Record<string, unknown>[];
  dimensions: BackendScopeDimension[];
  user_research_plan?: UserResearchPlan | null;
  frozen_at?: string | null;
}

interface BackendScopingDraft {
  scope_contract: BackendTaskScopeContract;
  clarification_questions: string[];
  rationale: string;
}

export interface ScopingDraftResult {
  contract: TaskScopeContract;
  rationale: string;
}

export async function createScopingDraft(input: {
  userBrief: string;
  knownCompetitors?: string[];
}): Promise<ScopingDraftResult> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/scoping`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_brief: input.userBrief,
      known_competitors: input.knownCompetitors ?? [],
      previous_draft: null,
      clarifications: [],
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to create scoping draft: ${response.status}`);
  }

  const draft = (await response.json()) as BackendScopingDraft;
  return {
    contract: fromBackendScopeContract(draft),
    rationale: draft.rationale,
  };
}

export function fromBackendScopeContract(draft: BackendScopingDraft): TaskScopeContract {
  return {
    task_id: draft.scope_contract.id,
    target_product: draft.scope_contract.target_product ?? null,
    competitors: draft.scope_contract.competitors.map((competitor) => competitor.name),
    user_brief: draft.scope_contract.user_brief,
    clarifications: draft.clarification_questions.map(
      (question, index): ClarifyingQuestion => ({
        id: `clarification_${index + 1}`,
        question,
        options: [],
        answer: null,
      }),
    ),
    dimensions: draft.scope_contract.dimensions.map(
      (dimension): DimensionSpec => ({
        id: dimension.id,
        layer: dimension.layer,
        source: dimension.source,
        title: dimension.title,
        intent: dimension.intent,
        schema_ref: dimension.schema_ref ?? null,
        enabled: dimension.enabled,
        locked: dimension.locked,
        order: dimension.order,
      }),
    ),
    user_research_plan:
      draft.scope_contract.user_research_plan ?? emptyUserResearchPlan(),
    frozen_at: draft.scope_contract.frozen_at ?? null,
  };
}

export function toBackendScopeContract(contract: TaskScopeContract): BackendTaskScopeContract {
  return {
    id: contract.task_id,
    user_brief: contract.user_brief,
    intent_mode: "mixed",
    target_product: contract.target_product,
    competitors: contract.competitors.map((name, index) => ({
      name,
      source: index === 0 ? "nl_extracted" : "ai_recommended",
      rationale: "Confirmed in frontend scoping page",
    })),
    clarifications: contract.clarifications.map((question) => ({
      id: question.id,
      question: question.question,
      answer: question.answer,
    })),
    dimensions: contract.dimensions.map((dimension) => ({
      id: dimension.id,
      title: dimension.title,
      intent: dimension.intent,
      layer: dimension.layer,
      order: dimension.order,
      enabled: dimension.enabled,
      locked: dimension.locked,
      source: dimension.source,
      schema_ref: dimension.schema_ref,
    })),
    user_research_plan: contract.user_research_plan,
    frozen_at: contract.frozen_at,
  };
}
