import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Fraunces } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { TopNav } from "@/components/layout/top-nav";
import { LanguageDocumentSync } from "@/components/layout/language-document-sync";
import { Toaster } from "@/components/ui/sonner";
import { AuthRouteGuard } from "@/components/auth/auth-route-guard";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

// Variable serif for headlines / brand. opsz axis: 9–144.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  display: "swap",
  axes: ["opsz", "SOFT", "WONK"],
});

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
      className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}
      suppressHydrationWarning
    >
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
