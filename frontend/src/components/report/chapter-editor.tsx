"use client";

import { useState } from "react";
import type { CorrectionType } from "@/lib/api/reports";
import { cn } from "@/lib/utils";

const CORRECTION_OPTIONS: { value: CorrectionType; label: string }[] = [
  { value: "fact_fix", label: "事实修正" },
  { value: "wording_improvement", label: "措辞改善" },
  { value: "additional_info", label: "补充信息" },
  { value: "remove_invalid", label: "移除无效内容" },
  { value: "structure_adjustment", label: "结构调整" },
];

interface ChapterEditorProps {
  initialContent: string;
  fieldPath: string;
  claimId: string;
  onSave: (payload: {
    claimId: string;
    fieldPath: string;
    newValue: string;
    correctionType: CorrectionType;
  }) => Promise<void>;
  onCancel: () => void;
}

export function ChapterEditor({
  initialContent,
  fieldPath: _fieldPath,
  claimId: _claimId,
  onSave,
  onCancel,
}: ChapterEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [correctionType, setCorrectionType] = useState<CorrectionType>("fact_fix");
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (saving) return;
    setSaving(true);
    try {
      await onSave({
        claimId: _claimId,
        fieldPath: _fieldPath,
        newValue: content,
        correctionType,
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-4 rounded-md border border-primary/30 bg-primary/4 overflow-hidden">
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={6}
        className={cn(
          "w-full resize-y px-4 py-3 bg-transparent text-[13.5px] leading-relaxed text-foreground",
          "border-b border-primary/20 outline-none",
          "placeholder:text-muted-foreground/50",
        )}
        aria-label="编辑章节内容"
      />
      <div className="flex items-center gap-3 px-4 py-2.5 flex-wrap">
        <select
          value={correctionType}
          onChange={(e) => setCorrectionType(e.target.value as CorrectionType)}
          className={cn(
            "flex-1 min-w-[160px] text-[12px] px-2.5 py-1.5 rounded border border-border/70",
            "bg-background text-foreground/80 outline-none",
          )}
          aria-label="修正类型"
        >
          {CORRECTION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <div className="flex gap-2 ml-auto">
          <button
            onClick={onCancel}
            className="text-[12px] px-3 py-1.5 rounded border border-border/70 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={cn(
              "text-[12px] px-3 py-1.5 rounded bg-primary text-primary-foreground",
              "hover:bg-primary/90 transition-colors",
              saving && "opacity-60 cursor-not-allowed",
            )}
          >
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
