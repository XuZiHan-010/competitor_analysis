"use client";

import { useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";
import { useLangStore } from "@/stores/lang-store";
import { useI18n } from "@/lib/i18n";

const subscribe = () => () => {};

export function LangToggle() {
  const { lang, toggle } = useLangStore();
  const { t } = useI18n();
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);

  if (!mounted) {
    return (
      <Button variant="ghost" size="sm" disabled className="w-10 text-xs font-medium tracking-wide">
        中
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggle}
      className="w-10 text-xs font-medium tracking-wide text-muted-foreground hover:text-foreground"
      aria-label={lang === "zh" ? t("switchToEnglish") : t("switchToChinese")}
    >
      {lang === "zh" ? "EN" : "中"}
    </Button>
  );
}
