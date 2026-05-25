"use client";

import Link from "next/link";
import { FileText, PlayCircle, User } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { ThemeToggle } from "./theme-toggle";
import { LangToggle } from "./lang-toggle";
import { useLangStore } from "@/stores/lang-store";
import { cn } from "@/lib/utils";

export function TopNav() {
  const { lang } = useLangStore();

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

          <Link
            href="/demo/scoping"
            className={cn(
              "ml-2 inline-flex items-center gap-1.5 rounded-md px-3 py-1.5",
              "text-base font-medium text-foreground/90 hover:text-foreground",
              "hover:bg-secondary/70 transition-colors",
            )}
          >
            <PlayCircle className="h-4 w-4 text-[var(--color-accent-warm)]" />
            {lang === "zh" ? "30秒demo演示" : "30s demo"}
          </Link>
        </nav>
      </div>
    </header>
  );
}
