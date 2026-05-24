"use client";

import Link from "next/link";
import { FileText, User } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { ThemeToggle } from "./theme-toggle";
import { LangToggle } from "./lang-toggle";
import { useLangStore } from "@/stores/lang-store";
import { cn } from "@/lib/utils";

export function TopNav() {
  const { lang } = useLangStore();

  return (
    <header className="border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40">
      <div className="mx-auto flex h-14 max-w-[1280px] items-center justify-between px-6">
        <Link
          href="/tasks/new"
          className="group flex items-baseline gap-2.5"
          aria-label="Strata 首页"
        >
          <span
            className="text-[22px] leading-none tracking-tight text-primary"
            style={{
              fontFamily: "var(--font-display)",
              fontVariationSettings: '"opsz" 144, "SOFT" 0',
              fontWeight: 500,
            }}
          >
            Strata
          </span>
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
            <span className="hidden sm:inline">
              {lang === "zh" ? "我的报告" : "My Reports"}
            </span>
          </Link>
          <LangToggle />
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full"
            aria-label={lang === "zh" ? "账户" : "Account"}
          >
            <User className="h-4 w-4" />
          </Button>
        </nav>
      </div>
    </header>
  );
}
