"use client";

import { Database, Library } from "lucide-react";
import { PageContainer } from "@/components/layout/page-container";
import { DataSourceCard } from "@/components/settings/data-source-card";
import { useI18n } from "@/lib/i18n";

export default function SettingsPage() {
  const { t } = useI18n();

  return (
    <PageContainer>
      <header className="mb-8">
        <p
          className="mb-3 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          Strata · {t("navSettings")}
        </p>
        <h1
          className="text-[2.4rem] leading-[1.05] tracking-tight text-foreground"
          style={{
            fontFamily: "var(--font-display)",
            fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
            fontWeight: 380,
            textWrap: "balance",
          }}
        >
          {t("settingsDataSourceTitle")}
        </h1>
        <p className="mt-3 max-w-[560px] text-sm leading-relaxed text-muted-foreground">
          {t("settingsDataSourceIntro")}
        </p>
        <div className="rule-fade mt-7" aria-hidden="true" />
      </header>

      <div className="space-y-2.5">
        <DataSourceCard
          icon={Database}
          status="enabled"
          statusLabel={t("settingsStatusEnabled")}
          title={t("settingsHistoryTitle")}
          description={t("settingsHistoryDesc")}
          meta={t("settingsHistoryMeta")}
        />
        <DataSourceCard
          icon={Library}
          status="roadmap"
          statusLabel={t("settingsStatusRoadmap")}
          title={t("settingsKbTitle")}
          description={t("settingsKbDesc")}
          meta={t("settingsKbMeta")}
        />
      </div>

      <p
        className="mt-6 text-[11px] uppercase leading-relaxed tracking-[0.1em] text-muted-foreground/55"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {t("settingsRoadmapNote")}
      </p>
    </PageContainer>
  );
}
