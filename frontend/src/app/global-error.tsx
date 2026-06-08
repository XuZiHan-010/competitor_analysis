"use client";

export default function GlobalError({
  reset,
}: Readonly<{
  error: Error & { digest?: string };
  reset: () => void;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <main
          className="min-h-screen bg-background text-foreground flex items-center justify-center px-6"
          role="alert"
        >
          <section className="w-full max-w-md space-y-5 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Strata
            </p>
            <h1 className="text-2xl font-semibold text-balance">
              页面暂时无法加载
            </h1>
            <p className="text-sm leading-6 text-muted-foreground">
              请重试当前操作。如果问题仍然存在，请稍后重新打开页面。
            </p>
            <button
              type="button"
              onClick={reset}
              className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              重试
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
