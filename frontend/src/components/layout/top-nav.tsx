"use client";

import Link from "next/link";
import { FileText, LogOut, PlayCircle, Search, Settings, User } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { ThemeToggle } from "./theme-toggle";
import { LangToggle } from "./lang-toggle";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

export function TopNav() {
  const { t } = useI18n();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  return (
    <header className="border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40">
      <div className="mx-auto flex h-14 max-w-[1280px] items-center justify-end px-6">
        <nav className="flex items-center gap-1">
          <Link
            href="/tasks"
            className={cn(
              buttonVariants({ variant: "ghost", size: "sm" }),
              "text-sm font-medium text-muted-foreground hover:text-foreground",
            )}
          >
            <FileText className="h-5 w-5" />
            <span className="hidden sm:inline">{t("navReports")}</span>
          </Link>
          <Link
            href="/reports"
            className={cn(
              buttonVariants({ variant: "ghost", size: "sm" }),
              "text-sm font-medium text-muted-foreground hover:text-foreground",
            )}
          >
            <Search className="h-5 w-5" />
            <span className="hidden sm:inline">{t("navReportSearch")}</span>
          </Link>
          <Link
            href="/settings"
            className={cn(
              buttonVariants({ variant: "ghost", size: "icon" }),
              "text-muted-foreground hover:text-foreground",
            )}
            aria-label={t("navSettings")}
          >
            <Settings className="h-5 w-5" />
          </Link>
          <LangToggle />
          <ThemeToggle />
          {user ? (
            <Button
              variant="ghost"
              size="sm"
              className="max-w-[180px] gap-2 rounded-full"
              aria-label="退出登录"
              onClick={() => void logout()}
            >
              <span className="hidden max-w-[120px] truncate text-xs md:inline">
                {user.email}
              </span>
              <LogOut className="h-4 w-4" />
            </Button>
          ) : (
            <Link
              href="/login"
              className={cn(
                buttonVariants({ variant: "ghost", size: "icon" }),
                "rounded-full",
              )}
              aria-label={t("navAccount")}
            >
              <User className="h-4 w-4" />
            </Link>
          )}

          <Link
            href="/demo/scoping"
            className={cn(
              "ml-2 inline-flex items-center gap-1.5 rounded-md px-3 py-1.5",
              "text-base font-medium text-foreground/90 hover:text-foreground",
              "hover:bg-secondary/70 transition-colors",
            )}
          >
            <PlayCircle className="h-4 w-4 text-[var(--color-accent-warm)]" />
            {t("navDemo")}
          </Link>
        </nav>
      </div>
    </header>
  );
}
