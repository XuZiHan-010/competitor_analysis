import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { ThemeProvider } from "next-themes";
import { TopNav } from "@/components/layout/top-nav";
import { LanguageDocumentSync } from "@/components/layout/language-document-sync";
import { Toaster } from "@/components/ui/sonner";
import { AuthRouteGuard } from "@/components/auth/auth-route-guard";
import "./globals.css";

export const metadata: Metadata = {
  title: "Strata — 竞品分析情报系统",
  description:
    "多 Agent 协作的结构化竞品分析平台。从需求描述到可溯源报告，全自动产出。",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "oklch(0.975 0.008 85)" },
    { media: "(prefers-color-scheme: dark)", color: "oklch(0.16 0.012 245)" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* Fraunces variable font — loaded at runtime, build-time blocked networks fall back to serif stack */}
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,100..900;1,9..144,100..900&display=swap"
          rel="stylesheet"
        />
        <style>{`:root { --font-fraunces: 'Fraunces', 'Noto Serif SC', 'PingFang SC', Georgia, serif; }`}</style>
      </head>
      <body className="min-h-full flex flex-col bg-paper-grain">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <LanguageDocumentSync />
          <AuthRouteGuard />
          <TopNav />
          <main className="flex-1 flex flex-col">{children}</main>
          <Toaster
            position="bottom-right"
            richColors
            closeButton
            theme="system"
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
