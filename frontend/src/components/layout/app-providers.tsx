"use client";

import dynamic from "next/dynamic";
import { ThemeProvider } from "next-themes";
import { AuthRouteGuard } from "@/components/auth/auth-route-guard";
import { LanguageDocumentSync } from "@/components/layout/language-document-sync";
import { Toaster } from "@/components/ui/sonner";

// @base-ui/react uses React.useContext at module init; skip SSR to avoid
// Turbopack null-React crash when prerendering /_not-found
const TopNav = dynamic(
  () => import("@/components/layout/top-nav").then((m) => ({ default: m.TopNav })),
  { ssr: false },
);

export function AppProviders({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <LanguageDocumentSync />
      <AuthRouteGuard />
      <TopNav />
      <main className="flex-1 flex flex-col">{children}</main>
      <Toaster position="bottom-right" richColors closeButton theme="system" />
    </ThemeProvider>
  );
}
