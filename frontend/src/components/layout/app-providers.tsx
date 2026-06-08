"use client";

import { ThemeProvider } from "next-themes";
import { AuthRouteGuard } from "@/components/auth/auth-route-guard";
import { LanguageDocumentSync } from "@/components/layout/language-document-sync";
import { TopNav } from "@/components/layout/top-nav";
import { Toaster } from "@/components/ui/sonner";

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
