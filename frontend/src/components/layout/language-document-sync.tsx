"use client";

import { useEffect } from "react";
import { htmlLang, useI18n } from "@/lib/i18n";
import { useLangStore } from "@/stores/lang-store";

export function LanguageDocumentSync() {
  const lang = useLangStore((s) => s.lang);
  const { t } = useI18n();

  useEffect(() => {
    document.documentElement.lang = htmlLang(lang);
    document.title = t("pageTitle");
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute("content", t("pageDescription"));
  }, [lang, t]);

  return null;
}
