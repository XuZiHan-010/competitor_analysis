"use client";

import { useState, type KeyboardEvent } from "react";
import { Plus, X } from "lucide-react";
import { useScopingStore } from "@/stores/scoping-store";
import { cn } from "@/lib/utils";

export function CompetitorChips() {
  const draftContract = useScopingStore((s) => s.draftContract);
  const { addCompetitor, removeCompetitor } = useScopingStore();

  const [draft, setDraft] = useState("");
  const [adding, setAdding] = useState(false);

  if (!draftContract) return null;
  const competitors = draftContract.competitors;

  function commit() {
    const trimmed = draft.trim();
    if (trimmed) addCompetitor(trimmed);
    setDraft("");
    setAdding(false);
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Escape") {
      setDraft("");
      setAdding(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span
        className="tabular text-xs uppercase tracking-[0.18em] text-muted-foreground mr-1"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        Subjects
      </span>
      {competitors.map((name) => (
        <span
          key={name}
          className={cn(
            "group inline-flex items-center gap-1.5 pl-3 pr-1.5 py-1",
            "bg-secondary text-secondary-foreground text-sm rounded",
            "border border-border/60",
          )}
        >
          <span className="font-medium">{name}</span>
          <button
            type="button"
            onClick={() => removeCompetitor(name)}
            className="rounded-sm p-0.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive/40"
            aria-label={`移除 ${name}`}
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}

      {adding ? (
        <input
          autoFocus
          type="text"
          name="competitor-name"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={onKey}
          placeholder="名称后 Enter…"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          aria-label="新增竞品名称"
          className={cn(
            "inline-flex h-7 min-w-[120px] px-2 text-sm",
            "bg-card border border-primary/40 rounded outline-none",
            "focus-visible:ring-2 focus-visible:ring-primary/20",
          )}
        />
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          aria-label="添加竞品"
          className={cn(
            "inline-flex items-center gap-1 px-2.5 py-1 text-sm",
            "border border-dashed border-border rounded",
            "text-muted-foreground hover:text-foreground hover:border-foreground/40",
            "transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
          )}
        >
          <Plus className="h-3 w-3" />
          添加
        </button>
      )}
    </div>
  );
}
