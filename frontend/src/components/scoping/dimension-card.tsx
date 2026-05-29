"use client";

import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Lock, Pencil, X, Check } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { DimensionSpec } from "@/lib/mocks/types";
import { useScopingStore } from "@/stores/scoping-store";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

interface DimensionCardProps {
  dimension: DimensionSpec;
  index: number;
}

export function DimensionCard({ dimension, index }: DimensionCardProps) {
  const { lang, t } = useI18n();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: dimension.id });

  const {
    toggleDimensionEnabled,
    updateDimensionTitle,
    updateDimensionIntent,
    removeDimension,
  } = useScopingStore();

  const displayTitle = dimension.title_i18n?.[lang] ?? dimension.title;
  const displayIntent = dimension.intent_i18n?.[lang] ?? dimension.intent;

  const [editingTitle, setEditingTitle] = useState(false);
  const [editingIntent, setEditingIntent] = useState(false);
  const [titleDraft, setTitleDraft] = useState(displayTitle);
  const [intentDraft, setIntentDraft] = useState(displayIntent);

  const titleRef = useRef<HTMLInputElement>(null);
  const intentRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editingTitle) titleRef.current?.focus();
  }, [editingTitle]);

  useEffect(() => {
    if (editingIntent) intentRef.current?.focus();
  }, [editingIntent]);

  // Keep draft in sync with the active language when not in edit mode
  useEffect(() => {
    if (!editingTitle) setTitleDraft(displayTitle);
  }, [displayTitle, editingTitle]);

  useEffect(() => {
    if (!editingIntent) setIntentDraft(displayIntent);
  }, [displayIntent, editingIntent]);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 50 : "auto",
  };

  const isCore = dimension.layer === "core";

  function commitTitle() {
    const trimmed = titleDraft.trim();
    if (trimmed && trimmed !== displayTitle) {
      updateDimensionTitle(dimension.id, trimmed);
    } else {
      setTitleDraft(displayTitle);
    }
    setEditingTitle(false);
  }

  function commitIntent() {
    const trimmed = intentDraft.trim();
    if (trimmed && trimmed !== displayIntent) {
      updateDimensionIntent(dimension.id, trimmed);
    } else {
      setIntentDraft(displayIntent);
    }
    setEditingIntent(false);
  }

  function onTitleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      commitTitle();
    } else if (e.key === "Escape") {
      setTitleDraft(dimension.title);
      setEditingTitle(false);
    }
  }

  function onIntentKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      commitIntent();
    } else if (e.key === "Escape") {
      setIntentDraft(dimension.intent);
      setEditingIntent(false);
    }
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "group relative grid grid-cols-[auto_auto_1fr_auto] items-start gap-2 px-3 py-3 sm:gap-4 sm:px-5 sm:py-4",
        "border border-border/70 rounded-md bg-card",
        "shadow-[0_1px_0_0_oklch(0.88_0.012_75_/_0.4)]",
        "transition-[box-shadow,opacity] duration-200",
        isDragging && "shadow-lg ring-2 ring-primary/20",
        !dimension.enabled && "opacity-55",
      )}
    >
      {/* Order number — editorial section numbering */}
      <span
        className={cn(
          "tabular self-center text-xs font-medium",
          "w-7 text-right",
          dimension.enabled ? "text-muted-foreground" : "text-muted-foreground/50",
        )}
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {String(index + 1).padStart(2, "0")}
      </span>

      {/* Checkbox */}
      <div className="self-center pt-0.5">
        <Checkbox
          checked={dimension.enabled}
          onCheckedChange={() => toggleDimensionEnabled(dimension.id)}
          disabled={dimension.locked}
          className={cn(
            "h-4 w-4 rounded-sm border-border",
            dimension.locked && "opacity-60 cursor-not-allowed",
          )}
          aria-label={t("disableOrEnableDimension", {
            action: dimension.enabled ? t("cancelAction") : "",
            title: displayTitle,
          })}
        />
      </div>

      {/* Title + Intent column */}
      <div className="min-w-0 space-y-1.5">
        <div className="flex items-baseline gap-2">
          {/* Layer marker */}
          {isCore ? (
            <Tooltip>
              <TooltipTrigger
                render={
                  <span
                    className={cn(
                      "inline-flex items-center justify-center h-5 w-5 rounded-sm",
                      "bg-primary/8 text-primary border border-primary/15",
                      "cursor-default",
                    )}
                    aria-label={t("coreDimension")}
                  />
                }
              >
                <Lock className="h-2.5 w-2.5" strokeWidth={2.5} />
              </TooltipTrigger>
              <TooltipContent side="top" className="text-xs">
                {t("coreDimensionTooltip")}
              </TooltipContent>
            </Tooltip>
          ) : (
            <Tooltip>
              <TooltipTrigger
                render={
                  <span
                    className={cn(
                      "inline-flex items-center justify-center h-5 w-5 rounded-sm",
                      "bg-accent-warm/12 border border-accent-warm/20 cursor-default",
                    )}
                    style={{ color: "var(--accent-warm)" }}
                    aria-label={t("extensionDimension")}
                  />
                }
              >
                <Pencil className="h-2.5 w-2.5" strokeWidth={2.5} />
              </TooltipTrigger>
              <TooltipContent side="top" className="text-xs">
                {t("extensionDimensionTooltip")}
              </TooltipContent>
            </Tooltip>
          )}

          {/* Title (inline-editable) */}
          {editingTitle ? (
            <input
              ref={titleRef}
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              onBlur={commitTitle}
              onKeyDown={onTitleKey}
              autoComplete="off"
              spellCheck={false}
              aria-label={t("editSectionTitle")}
              className={cn(
                "flex-1 min-w-0 bg-transparent border-b border-primary",
                "text-[15px] font-semibold leading-tight",
                "outline-none px-0.5 -mb-px",
              )}
              style={{ fontFamily: "var(--font-display)" }}
            />
          ) : (
            <button
              type="button"
              onClick={() => setEditingTitle(true)}
              aria-label={t("editTitleWithName", { title: displayTitle })}
              className={cn(
                "flex-1 min-w-0 text-left text-[15px] font-semibold leading-tight",
                "border-b border-transparent hover:border-border",
                "transition-colors px-0.5 -mb-px truncate",
                "focus-visible:outline-none focus-visible:border-primary/60",
              )}
              style={{ fontFamily: "var(--font-display)" }}
            >
              {displayTitle}
            </button>
          )}

          {dimension.schema_ref && (
            <code
              className={cn(
                "tabular hidden md:inline text-[10px] text-muted-foreground/70",
                "px-1.5 py-0.5 rounded bg-muted/50 border border-border/40",
              )}
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {dimension.schema_ref}
            </code>
          )}
        </div>

        {/* Intent (inline-editable) */}
        {editingIntent ? (
          <div className="relative">
            <textarea
              ref={intentRef}
              value={intentDraft}
              onChange={(e) => setIntentDraft(e.target.value)}
              onBlur={commitIntent}
              onKeyDown={onIntentKey}
              rows={2}
              aria-label={t("editIntentDescription")}
              className={cn(
                "w-full resize-none bg-transparent",
                "text-sm leading-snug text-muted-foreground italic",
                "border-l-2 border-primary pl-3 pr-12 py-0.5",
                "outline-none",
              )}
              placeholder={t("intentInlinePlaceholder")}
            />
            <Check className="absolute top-1.5 right-1.5 h-3.5 w-3.5 text-primary/60" />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setEditingIntent(true)}
            aria-label={t("editIntent")}
            className={cn(
              "block w-full text-left",
              "text-sm leading-snug text-muted-foreground italic",
              "border-l-2 border-border hover:border-primary/60",
              "pl-3 pr-2 py-0.5",
              "transition-colors",
              "group-hover:border-primary/40",
              "focus-visible:outline-none focus-visible:border-primary",
            )}
          >
            {displayIntent || (
              <span className="text-muted-foreground/50">
                {t("addIntentDescription")}
              </span>
            )}
          </button>
        )}
      </div>

      {/* Right-side controls */}
      <div className="flex flex-col items-center gap-1 self-stretch -mr-1">
        <button
          type="button"
          {...attributes}
          {...listeners}
          className={cn(
            "cursor-grab active:cursor-grabbing p-1 rounded",
            "text-muted-foreground/50 hover:text-foreground hover:bg-muted",
            "transition-colors",
            "touch-none",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
          )}
          aria-label={t("dragToSort")}
        >
          <GripVertical className="h-4 w-4" />
        </button>

        {isCore ? (
          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  type="button"
                  className={cn(
                    "p-1 rounded text-muted-foreground/30",
                    "cursor-not-allowed",
                  )}
                  aria-label={t("coreCannotDelete")}
                  aria-disabled="true"
                  onClick={(e) => e.preventDefault()}
                />
              }
            >
              <X className="h-4 w-4" />
            </TooltipTrigger>
            <TooltipContent side="left" className="text-xs">
              {t("coreCannotDelete")}
            </TooltipContent>
          </Tooltip>
        ) : (
          <button
            type="button"
            onClick={() => removeDimension(dimension.id)}
            className={cn(
              "p-1 rounded text-muted-foreground/50",
              "hover:text-destructive hover:bg-destructive/10",
              "transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive/40",
            )}
            aria-label={t("deleteDimension", { title: displayTitle })}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
