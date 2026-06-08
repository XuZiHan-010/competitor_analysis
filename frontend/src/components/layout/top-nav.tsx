"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Home, PlayCircle, Search } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

// @base-ui/react uses React.useContext at module init; skip SSR to avoid Turbopack null-React issue
const AccountMenu = dynamic(
  () => import("./account-menu").then((m) => ({ default: m.AccountMenu })),
  { ssr: false },
);

export function TopNav() {
  const { t } = useI18n();
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  const demoLink = (
    <Link
      href="/demo/scoping"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5",
        "text-base font-medium text-foreground/90 hover:text-foreground",
        "hover:bg-secondary/70 transition-colors",
      )}
    >
      <PlayCircle className="h-4 w-4 text-[var(--color-accent-warm)]" />
      {t("navDemo")}
    </Link>
  );

  // Logged-out login screen: minimal chrome — brand wordmark + demo entry +
  // theme/language switch only. App routes (reports/search) stay hidden.
  if (isLogin) {
    return (
      <header className="border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40">
        <div className="mx-auto flex h-14 max-w-[1280px] items-center justify-end px-6">
          <nav className="flex items-center gap-1">
            {demoLink}
            <AccountMenu />
          </nav>
        </div>
      </header>
    );
  }

  return (
    <header className="border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40">
      <div className="mx-auto flex h-14 max-w-[1280px] items-center justify-between px-6">
        <Link
          href="/tasks/new"
          className="inline-flex items-center gap-2 text-[13px] font-semibold tracking-[0.08em] uppercase text-foreground/80 hover:text-foreground transition-colors"
          style={{ fontFamily: "var(--font-mono)" }}
          title="返回主页"
        >
          <Home className="h-4 w-4" />
          Strata
        </Link>
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

          <span className="ml-2">{demoLink}</span>

          <AccountMenu />
        </nav>
      </div>
    </header>
  );
}
