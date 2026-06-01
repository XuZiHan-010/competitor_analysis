"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { Database, LogIn, LogOut, Monitor, Moon, Settings, Sun } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuLinkItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/lib/i18n";
import { useLangStore } from "@/stores/lang-store";
import { useAuthStore } from "@/stores/auth-store";

const subscribe = () => () => {};

export function AccountMenu() {
  const { t } = useI18n();
  const { theme, setTheme } = useTheme();
  const lang = useLangStore((state) => state.lang);
  const setLang = useLangStore((state) => state.setLang);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);

  // Auth/theme/lang are client-only state; render a stable placeholder until
  // mounted so the trigger glyph and radio selection don't hydration-mismatch.
  const triggerLabel = mounted ? (user ? user.email : t("accountMenu")) : t("accountMenu");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={triggerLabel}
        className="ml-1 inline-flex size-9 touch-manipulation items-center justify-center rounded-full text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 aria-expanded:bg-muted aria-expanded:text-foreground"
      >
        <Settings className="size-4" aria-hidden="true" />
      </DropdownMenuTrigger>

      <DropdownMenuContent>
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <span className="block truncate normal-case tracking-normal text-foreground/90">
              {mounted && user ? user.email : t("accountGuest")}
            </span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>

        {mounted && user ? (
          <DropdownMenuLinkItem render={<Link href="/settings" />} closeOnClick>
            <Database aria-hidden="true" />
            {t("settingsDataSourceTitle")}
          </DropdownMenuLinkItem>
        ) : null}

        <DropdownMenuSeparator />

        <DropdownMenuRadioGroup
          value={mounted ? (theme ?? "system") : "system"}
          onValueChange={(value) => setTheme(String(value))}
        >
          <DropdownMenuLabel>{t("menuTheme")}</DropdownMenuLabel>
          <DropdownMenuRadioItem value="light">
            <Sun aria-hidden="true" />
            {t("themeLight")}
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="dark">
            <Moon aria-hidden="true" />
            {t("themeDark")}
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="system">
            <Monitor aria-hidden="true" />
            {t("themeSystem")}
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>

        <DropdownMenuSeparator />

        <DropdownMenuRadioGroup
          value={mounted ? lang : "zh"}
          onValueChange={(value) => setLang(value === "en" ? "en" : "zh")}
        >
          <DropdownMenuLabel>{t("menuLanguage")}</DropdownMenuLabel>
          <DropdownMenuRadioItem value="zh">{t("langChinese")}</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="en">{t("langEnglish")}</DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>

        <DropdownMenuSeparator />

        {mounted && user ? (
          <DropdownMenuItem onClick={() => void logout()}>
            <LogOut aria-hidden="true" />
            {t("navLogout")}
          </DropdownMenuItem>
        ) : (
          <DropdownMenuLinkItem render={<Link href="/login" />} closeOnClick>
            <LogIn aria-hidden="true" />
            {t("navSignIn")}
          </DropdownMenuLinkItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
