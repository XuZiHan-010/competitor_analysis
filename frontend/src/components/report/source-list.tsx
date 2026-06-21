import { ExternalLink } from "lucide-react";
import type { ReportSource, SourceType } from "@/lib/api/reports";

interface SourceListProps {
  sources: ReportSource[];
}

const FACTUAL_TYPES: SourceType[] = [
  "official",
  "commercial",
  "media",
  "tech_community",
  "user_feedback",
  "user_uploaded",
];

const USER_VOICE_TYPES: SourceType[] = ["app_review", "public_review", "published_survey"];

const SIMULATED_TYPES: SourceType[] = ["ai_simulated"];

function isSimulated(s: ReportSource): boolean {
  return (
    SIMULATED_TYPES.includes(s.type) ||
    s.provider.toLowerCase().includes("fallback") ||
    s.provider.toLowerCase().includes("simulated")
  );
}

function SourceItem({ s, globalIndex }: { s: ReportSource; globalIndex: number }) {
  return (
    <li
      key={s.id}
      id={s.id}
      className="grid grid-cols-[auto_1fr] gap-x-3 text-[12.5px] leading-relaxed scroll-mt-20"
    >
      <span
        className="tabular text-muted-foreground/60 tabular-nums"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {globalIndex + 1}.
      </span>
      <div className="min-w-0">
        <a
          href={s.url ?? undefined}
          target="_blank"
          rel="noreferrer noopener"
          className="text-foreground/90 hover:text-primary inline-flex items-baseline gap-1 underline decoration-border underline-offset-4 hover:decoration-primary"
        >
          {s.title}
          {s.url && (
            <ExternalLink className="h-3 w-3 self-center shrink-0" aria-hidden="true" />
          )}
        </a>
        <p
          className="text-[10.5px] text-muted-foreground/55 break-all mt-0.5"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {s.id}
        </p>
      </div>
    </li>
  );
}

function SourceGroup({
  title,
  sources,
  offset,
}: {
  title: string;
  sources: ReportSource[];
  offset: number;
}) {
  if (!sources.length) return null;
  return (
    <div className="space-y-3">
      <p
        className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground/60"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {title}
      </p>
      <ol className="space-y-3.5">
        {sources.map((s, i) => (
          <SourceItem key={s.id} s={s} globalIndex={offset + i} />
        ))}
      </ol>
    </div>
  );
}

export function SourceList({ sources }: SourceListProps) {
  if (!sources.length) return null;

  const factual = sources.filter(
    (s) => FACTUAL_TYPES.includes(s.type) && !isSimulated(s),
  );
  const userVoice = sources.filter((s) => USER_VOICE_TYPES.includes(s.type));
  const simulated = sources.filter(isSimulated);

  return (
    <section
      id="sources"
      aria-labelledby="sources-title"
      className="mt-16 pt-8 border-t border-border/60"
    >
      <h2
        id="sources-title"
        className="text-[1.2rem] mb-7 text-foreground/95"
        style={{
          fontFamily: "var(--font-display)",
          fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
          fontWeight: 400,
        }}
      >
        溯源
      </h2>
      <div className="space-y-8">
        <SourceGroup title="报告正文来源" sources={factual} offset={0} />
        <SourceGroup
          title="用户声音来源"
          sources={userVoice}
          offset={factual.length}
        />
        <SourceGroup
          title="模拟 / 兜底来源"
          sources={simulated}
          offset={factual.length + userVoice.length}
        />
      </div>
    </section>
  );
}
