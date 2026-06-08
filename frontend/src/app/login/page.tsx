"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { PageContainer } from "@/components/layout/page-container";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/stores/auth-store";

const DEMO_EMAIL = "example@email.com";

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const authError = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);

  const [submitting, setSubmitting] = useState(false);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();
    setSubmitting(true);
    try {
      await login(DEMO_EMAIL);
      toast.success("登录成功");
      router.replace(getSafeNextPath());
    } catch {
      toast.error("登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageContainer>
      <section className="mx-auto grid min-h-[calc(100vh-8rem)] w-full max-w-[920px] items-center gap-12 py-10 lg:grid-cols-[0.92fr_1.08fr] lg:gap-16">
        <div className="motion-safe:animate-[fade-in_0.5s_ease-out]">
          <h1
            className="text-[4.5rem] leading-[0.92] text-foreground sm:text-[6rem]"
            style={{
              fontFamily: "var(--font-display)",
              fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
              fontWeight: 440,
              letterSpacing: "-0.02em",
            }}
          >
            Strata
          </h1>
          <p className="mt-6 text-base tracking-[0.06em] text-muted-foreground">
            登录 AI 竞品报告分析系统
          </p>
          <div className="rule-fade mt-9" aria-hidden="true" />
        </div>

        <div className="rounded-xl border border-border/70 bg-card/70 p-6 shadow-sm motion-safe:animate-[slide-up_0.5s_cubic-bezier(0.16,1,0.3,1)] sm:p-8">
          <div className="mb-7">
            <h2 className="text-xl font-medium text-foreground">一键进入</h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              使用内置演示账号直接登录，无需验证码。
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleLogin}>
            <div className="space-y-2">
              <Label htmlFor="email">登录邮箱</Label>
              <div
                id="email"
                className="flex h-11 items-center rounded-md border border-border/60 bg-background/70 px-3.5 text-base tracking-[0.02em] text-foreground"
              >
                {DEMO_EMAIL}
              </div>
            </div>
            <Button
              type="submit"
              className="h-11 w-full justify-between text-base hover:bg-primary/90"
              disabled={submitting}
            >
              {submitting ? "登录中…" : "登录"}
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
            </Button>
          </form>

          {authError && (
            <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
              {authError}
            </p>
          )}
        </div>
      </section>
    </PageContainer>
  );
}

function getSafeNextPath(): string {
  if (typeof window === "undefined") return "/tasks";
  const next = new URL(window.location.href).searchParams.get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//")) return "/tasks";
  return next;
}
