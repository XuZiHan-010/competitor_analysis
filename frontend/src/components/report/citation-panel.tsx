"use client";

import { useEffect } from "react";
import { ExternalLink, X } from "lucide-react";
import { useCitationPanelStore } from "@/stores/citation-panel-store";
import type { ReportSource, SourceType } from "@/lib/api/reports";
import { TierBadge, tierOf } from "@/components/report/source-tier";
import { cn } from "@/lib/utils";

interface CitationPanelProps {
  sources: ReportSource[];
}

const USER_VOICE_TYPES: SourceType[] = ["app_review", "public_review", "ai_simulated"];

const TYPE_LABEL: Record<SourceType, string> = {
  official: "官方来源",
  commercial: "商业页面",
  media: "媒体报道",
  user_feedback: "用户反馈",
  tech_community: "技术社区",
  user_uploaded: "用户上传",
  published_survey: "调研报告",
  public_review: "公开评论",
  app_review: "应用评论",
  ai_simulated: "AI模拟",
};

export function CitationPanel({ sources }: CitationPanelProps) {
  const { openSourceId, close } = useCitationPanelStore();

  const source = openSourceId ? sources.find((s) => s.id === openSourceId) : null;
  const isOpen = !!source;

  // Sync URL hash → panel open state on mount
  useEffect(() => {
    const hash = window.location.hash;
    const match = hash.match(/^#citation=(.+)$/);
    if (match) {
      useCitationPanelStore.getState().open(decodeURIComponent(match[1]));
    }
  }, []);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, close]);

  const isUserVoice = source ? USER_VOICE_TYPES.includes(source.type) : false;

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={close}
        className={cn(
          "fixed inset-0 z-40 bg-background/40 backdrop-blur-[2px] transition-opacity duration-200",
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
        )}
      />

      {/* Panel */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="来源详情"
        aria-hidden={!isOpen}
        className={cn(
          "fixed right-0 top-0 bottom-0 z-50 w-[360px] max-w-[90vw]",
          "bg-card border-l border-border/60 shadow-xl",
          "flex flex-col transition-transform duration-250 ease-[cubic-bezier(0.16,1,0.3,1)]",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border/60">
          <p
            className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            来源 · {openSourceId}
          </p>
          <button
            onClick={close}
            aria-label="关闭来源面板"
            className="h-7 w-7 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-5">
          {source ? (
            <div className="space-y-4">
              {/* Title — link only when URL is present */}
              <div>
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-start gap-2 text-[14px] leading-snug text-foreground/95 hover:text-primary underline decoration-border underline-offset-4 hover:decoration-primary"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {source.title}
                    <ExternalLink className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden="true" />
                  </a>
                ) : (
                  <p
                    className="text-[14px] leading-snug text-foreground/95"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {source.title}
                  </p>
                )}
              </div>

              {/* Snippet */}
              <p className="text-[12.5px] text-muted-foreground leading-relaxed">
                {source.snippet}
              </p>

              {/* User-voice label */}
              {isUserVoice && (
                <div className="rounded border border-border/50 bg-muted/30 px-3 py-2">
                  <p
                    className="text-[11px] text-muted-foreground"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    ⚠ 用户声音来源 — 内容来自公开评论或模拟数据，仅供参考
                  </p>
                </div>
              )}

              {/* Metadata */}
              <div className="pt-2 border-t border-border/40 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <TierBadge tier={tierOf(source)} />
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded border",
                      source.valid
                        ? "border-primary/30 text-primary bg-primary/8"
                        : "border-destructive/30 text-destructive bg-destructive/8",
                    )}
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {source.valid ? "有效" : "无效"}
                  </span>
                  <span
                    className="text-[10px] text-muted-foreground/70 border border-border/50 rounded px-1.5 py-0.5"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {TYPE_LABEL[source.type] ?? source.type}
                  </span>
                  <span
                    className="text-[10px] text-muted-foreground/60"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {source.category}
                  </span>
                </div>
                <div
                  className="text-[10px] text-muted-foreground/50 space-y-0.5"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  <p>provider: {source.provider}</p>
                  {source.dimension_id && <p>dimension: {source.dimension_id}</p>}
                  {source.fetched_at && (
                    <p>fetched: {new Date(source.fetched_at).toLocaleDateString("zh-CN")}</p>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </aside>
    </>
  );
}
