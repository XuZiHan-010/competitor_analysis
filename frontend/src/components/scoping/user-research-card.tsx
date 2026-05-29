"use client";

import { Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  Questionnaire,
  SurveyQuestion,
  UserResearchPlan,
} from "@/lib/mocks/types";
import { UploadDropzone } from "./upload-dropzone";

const QUESTION_TYPES: { value: SurveyQuestion["type"]; label: string }[] = [
  { value: "open", label: "开放题" },
  { value: "multiple_choice", label: "单选题" },
  { value: "scale", label: "量表题" },
];

function newQuestion(): SurveyQuestion {
  return {
    id: `sq_${Math.random().toString(36).slice(2, 10)}`,
    text: "",
    type: "open",
    intent: "用户主动反馈",
  };
}

function ensureQuestionnaire(
  plan: UserResearchPlan,
  competitor: string,
): Questionnaire {
  return (
    plan.questionnaire ?? {
      id: `qn_${Math.random().toString(36).slice(2, 10)}`,
      competitor,
      dimension_intent: "用户研究：满意度、痛点与未满足需求",
      questions: [],
      design_rationale: "用户在立项页手动配置的研究问卷",
    }
  );
}

/**
 * 方案 C user-research plan editor: an enable switch, an inline questionnaire
 * builder, and a first-party upload zone. Disabling keeps the configured plan
 * but greys it out; the contract freezes with `enabled: false` so the backend
 * skips the SurveyTool branch entirely.
 */
export function UserResearchCard({
  value,
  onChange,
  contractId,
  competitors,
}: {
  value: UserResearchPlan;
  onChange: (plan: UserResearchPlan) => void;
  /** Server-issued contract id; uploads are disabled until it exists. */
  contractId: string;
  competitors: string[];
}) {
  const competitor = competitors[0] ?? "全部竞品";
  const questionnaire = value.questionnaire;
  const questions = questionnaire?.questions ?? [];
  // The offline fallback contract uses a client-fake `task_<ts>` id which the
  // upload endpoint can't accept; a real run carries a server UUID.
  const canUpload = value.enabled && !contractId.startsWith("task_");

  function setEnabled(enabled: boolean) {
    if (enabled) {
      onChange({
        ...value,
        enabled: true,
        questionnaire: ensureQuestionnaire(value, competitor),
      });
    } else {
      onChange({ ...value, enabled: false });
    }
  }

  function updateQuestions(next: SurveyQuestion[]) {
    const base = ensureQuestionnaire(value, competitor);
    onChange({ ...value, questionnaire: { ...base, questions: next } });
  }

  function addQuestion() {
    updateQuestions([...questions, newQuestion()]);
  }

  function editQuestion(id: string, patch: Partial<SurveyQuestion>) {
    updateQuestions(questions.map((q) => (q.id === id ? { ...q, ...patch } : q)));
  }

  function removeQuestion(id: string) {
    updateQuestions(questions.filter((q) => q.id !== id));
  }

  return (
    <div className="space-y-4">
      {/* Enable switch */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[13.5px] text-foreground/90">
            发起用户研究（方案 C）
          </p>
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
            启用后 SurveyTool 会优先使用你上传的一手数据，其次公开调研/评论，最后才用 AI 模拟兜底。
          </p>
        </div>
        <Switch checked={value.enabled} onChange={setEnabled} label="启用用户研究" />
      </div>

      {/* Body — greyed when disabled but kept mounted so config persists */}
      <div
        className={cn(
          "space-y-5",
          !value.enabled && "pointer-events-none select-none opacity-45",
        )}
        aria-hidden={!value.enabled}
      >
        {/* Questionnaire editor */}
        <div>
          <div className="mb-2.5 flex items-center justify-between">
            <p
              className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              问卷题目 · {questions.length}
            </p>
            <button
              type="button"
              disabled={!value.enabled}
              onClick={addQuestion}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border border-dashed border-primary/40 px-2 py-1",
                "text-[12px] text-primary transition-colors hover:bg-primary/8",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
              )}
            >
              <Plus className="h-3 w-3" />
              添加题目
            </button>
          </div>

          {questions.length === 0 ? (
            <p className="rounded-md border border-dashed border-border/60 px-3 py-4 text-center text-[12px] text-muted-foreground">
              还没有题目。点「添加题目」开始，或直接上传已有问卷结果。
            </p>
          ) : (
            <ul className="space-y-2">
              {questions.map((q, i) => (
                <li
                  key={q.id}
                  className="flex items-start gap-2 rounded-md border border-border/60 bg-card/50 px-3 py-2.5"
                >
                  <span
                    className="mt-2 shrink-0 text-[10px] tabular text-muted-foreground/70"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="flex-1 space-y-2">
                    <input
                      type="text"
                      value={q.text}
                      disabled={!value.enabled}
                      placeholder="输入问题，例如：你最常使用该产品的哪个功能？"
                      onChange={(e) => editQuestion(q.id, { text: e.target.value })}
                      className={cn(
                        "w-full rounded border border-border/50 bg-background px-2.5 py-1.5 text-[13px]",
                        "placeholder:text-muted-foreground/50",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                      )}
                    />
                    <div className="flex gap-1.5">
                      {QUESTION_TYPES.map((t) => (
                        <button
                          key={t.value}
                          type="button"
                          disabled={!value.enabled}
                          aria-pressed={q.type === t.value}
                          onClick={() => editQuestion(q.id, { type: t.value })}
                          className={cn(
                            "rounded px-2 py-0.5 text-[11px] transition-colors",
                            q.type === t.value
                              ? "bg-primary/10 text-foreground"
                              : "text-muted-foreground hover:text-foreground/80",
                          )}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={!value.enabled}
                    aria-label={`删除第 ${i + 1} 题`}
                    onClick={() => removeQuestion(q.id)}
                    className="mt-1 shrink-0 rounded p-1 text-muted-foreground/60 transition-colors hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* First-party upload */}
        <div>
          <p
            className="mb-2.5 text-[10px] uppercase tracking-[0.18em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            上传一手数据（可选）
          </p>
          <UploadDropzone contractId={contractId} disabled={!canUpload} />
          {value.enabled && !canUpload && (
            <p className="mt-1.5 text-[11px] text-muted-foreground/70">
              ScopingAgent 未连通时无法上传，可先编辑问卷，连通后再上传。
            </p>
          )}
        </div>

        {/* prefer_upload hint toggle */}
        <label className="flex items-center gap-2 text-[12px] text-muted-foreground">
          <input
            type="checkbox"
            checked={value.prefer_upload}
            disabled={!value.enabled}
            onChange={(e) => onChange({ ...value, prefer_upload: e.target.checked })}
            className="h-3.5 w-3.5 rounded border-border accent-primary"
          />
          我会提供一手问卷/访谈数据（优先采用，而非公开来源）
        </label>
      </div>
    </div>
  );
}

function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        checked ? "bg-primary" : "bg-border",
      )}
    >
      <span
        className={cn(
          "inline-block h-3.5 w-3.5 rounded-full bg-background transition-transform",
          checked ? "translate-x-[18px]" : "translate-x-[3px]",
        )}
      />
    </button>
  );
}
