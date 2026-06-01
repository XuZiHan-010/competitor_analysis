"use client";

import { useRef, useState } from "react";
import { CheckCircle2, FileUp, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import {
  uploadSurveyEvidence,
  type SurveyUploadKind,
} from "@/lib/api/survey";

const KINDS: { value: SurveyUploadKind; label: string }[] = [
  { value: "questionnaire_result", label: "问卷结果" },
  { value: "interview_record", label: "访谈记录" },
];

const ACCEPT = ".csv,.txt,.md";

interface UploadedFile {
  name: string;
  kind: SurveyUploadKind;
  evidenceCount: number;
}

/**
 * Uploads first-party survey/interview text as `user_uploaded_primary` evidence.
 * Reads the file client-side and POSTs its text to the contract-keyed endpoint.
 * Disabled until a server-issued contract id exists (no anonymous uploads).
 */
export function UploadDropzone({
  contractId,
  disabled = false,
}: {
  contractId: string;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [kind, setKind] = useState<SurveyUploadKind>("questionnaire_result");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploaded, setUploaded] = useState<UploadedFile[]>([]);

  async function handleFile(file: File) {
    if (busy || disabled) return;
    setBusy(true);
    try {
      const content = await file.text();
      const result = await uploadSurveyEvidence(contractId, kind, content);
      setUploaded((prev) => [
        ...prev,
        { name: file.name, kind, evidenceCount: result.parsed_evidence_count },
      ]);
      toast.success(`已上传「${file.name}」`, {
        description: `解析出 ${result.parsed_evidence_count} 条一手证据`,
      });
    } catch {
      toast.error("上传失败", {
        description: "请确认文件为 CSV / TXT / MD 文本，且后端可用。",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-1.5">
        {KINDS.map((k) => (
          <button
            key={k.value}
            type="button"
            disabled={disabled}
            aria-pressed={kind === k.value}
            onClick={() => setKind(k.value)}
            className={cn(
              "rounded-md border px-2.5 py-1 text-[12px] transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
              kind === k.value
                ? "border-primary/50 bg-primary/8 text-foreground"
                : "border-border/60 text-muted-foreground hover:text-foreground/80",
            )}
          >
            {k.label}
          </button>
        ))}
      </div>

      <button
        type="button"
        disabled={disabled || busy}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) void handleFile(file);
        }}
        className={cn(
          "flex w-full flex-col items-center gap-1.5 rounded-md border border-dashed px-4 py-6 text-center transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
          disabled && "cursor-not-allowed opacity-50",
          dragging
            ? "border-primary/60 bg-primary/8"
            : "border-border/70 hover:border-primary/40 hover:bg-card/60",
        )}
      >
        {busy ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : (
          <FileUp className="h-5 w-5 text-muted-foreground" />
        )}
        <span className="text-[13px] text-foreground/85">
          拖拽或点击上传{kind === "questionnaire_result" ? "问卷结果" : "访谈记录"}
        </span>
        <span
          className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground/70"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          CSV · TXT · MD
        </span>
      </button>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = "";
        }}
      />

      {uploaded.length > 0 && (
        <ul className="space-y-1.5">
          {uploaded.map((f, i) => (
            <li
              key={f.name + i}
              className="flex items-center gap-2 rounded-md border border-[oklch(0.62_0.17_145)]/30 bg-[oklch(0.62_0.17_145)]/8 px-3 py-2 text-[12px]"
            >
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[oklch(0.62_0.17_145)]" />
              <span className="truncate text-foreground/90">{f.name}</span>
              <span
                className="ml-auto shrink-0 rounded bg-[oklch(0.62_0.17_145)]/12 px-1.5 py-0.5 text-[10px] text-[oklch(0.5_0.15_145)]"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                一手 · {f.evidenceCount} 条
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
