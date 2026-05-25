"use client";

import { useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";
import { useLangStore } from "@/stores/lang-store";

const subscribe = () => () => {};

export function LangToggle() {
  const { lang, toggle } = useLangStore();
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
      aria-label={lang === "zh" ? "Switch to English" : "切换到中文"}
    >
      {lang === "zh" ? "EN" : "中"}
    </Button>
  );
}
