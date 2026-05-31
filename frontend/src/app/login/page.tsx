"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, KeyRound, Loader2, Mail } from "lucide-react";
import { toast } from "sonner";
import { PageContainer } from "@/components/layout/page-container";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/stores/auth-store";

type LoginStep = "email" | "code";

export default function LoginPage() {
  const router = useRouter();
  const requestCode = useAuthStore((state) => state.requestCode);
  const verify = useAuthStore((state) => state.verify);
  const devCode = useAuthStore((state) => state.devCode);
  const authError = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);

  const [step, setStep] = useState<LoginStep>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const normalizedEmail = useMemo(() => email.trim().toLowerCase(), [email]);
  const canSend = normalizedEmail.includes("@") && normalizedEmail.includes(".");
  const canVerify = canSend && code.trim().length >= 4;

  async function handleSendCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSend) return;
    clearError();
    setSubmitting(true);
    try {
      await requestCode(normalizedEmail);
      setStep("code");
      toast.success("验证码已发送");
    } catch {
      toast.error("验证码发送失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canVerify) return;
    clearError();
    setSubmitting(true);
    try {
      await verify(normalizedEmail, code.trim());
      toast.success("登录成功");
      router.replace(getSafeNextPath());
    } catch {
      toast.error("验证码无效或已过期");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageContainer>
      <section className="mx-auto grid min-h-[calc(100vh-8rem)] w-full max-w-[960px] items-center gap-10 py-10 lg:grid-cols-[0.95fr_1.05fr]">
        <div>
          <p
            className="mb-4 text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            Strata Access
          </p>
          <h1
            className="text-[2.45rem] leading-[1.04] text-foreground sm:text-[3.4rem]"
            style={{
              fontFamily: "var(--font-display)",
              fontVariationSettings: '"opsz" 144, "SOFT" 0, "WONK" 0',
              fontWeight: 410,
              textWrap: "balance",
            }}
          >
            登录竞品情报工作台
          </h1>
          <p className="mt-5 max-w-[52ch] text-sm leading-7 text-muted-foreground">
            使用邮箱验证码进入任务列表、实时 DAG 和可溯源报告。登录态由后端
            httpOnly cookie 托管，前端只负责发起会话校验。
          </p>
          <div className="rule-fade mt-8" aria-hidden="true" />
        </div>

        <div className="rounded-md border border-border/70 bg-card/70 p-5 shadow-sm sm:p-6">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <p
                className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {step === "email" ? "Step 01" : "Step 02"}
              </p>
              <h2 className="mt-1 text-lg font-medium text-foreground">
                {step === "email" ? "接收验证码" : "输入验证码"}
              </h2>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-background">
              {step === "email" ? (
                <Mail className="h-4 w-4 text-muted-foreground" />
              ) : (
                <KeyRound className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </div>

          {step === "email" ? (
            <form className="space-y-5" onSubmit={handleSendCode}>
              <div className="space-y-2">
                <Label htmlFor="email">邮箱</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  autoComplete="email"
                  placeholder="eric@example.com"
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
              <Button className="w-full justify-between" disabled={!canSend || submitting}>
                {submitting ? "发送中" : "发送验证码"}
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4" />
                )}
              </Button>
            </form>
          ) : (
            <form className="space-y-5" onSubmit={handleVerify}>
              <div className="rounded-md border border-border/60 bg-background/70 px-3 py-2 text-sm text-muted-foreground">
                验证码已发送至 <span className="text-foreground">{normalizedEmail}</span>
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">验证码</Label>
                <Input
                  id="code"
                  inputMode="numeric"
                  value={code}
                  autoComplete="one-time-code"
                  placeholder="6 位数字"
                  onChange={(event) => setCode(event.target.value)}
                />
              </div>
              {devCode && (
                <div className="flex items-center gap-2 rounded-md border border-primary/20 bg-primary/8 px-3 py-2 text-xs text-primary">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  开发环境验证码：{devCode}
                </div>
              )}
              <Button className="w-full justify-between" disabled={!canVerify || submitting}>
                {submitting ? "验证中" : "进入工作台"}
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4" />
                )}
              </Button>
              <button
                type="button"
                className="text-xs text-muted-foreground transition-colors hover:text-foreground"
                onClick={() => {
                  setStep("email");
                  setCode("");
                }}
              >
                换一个邮箱
              </button>
            </form>
          )}

          {authError && (
            <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {authError}
            </p>
          )}

          <div className="mt-6 flex items-center justify-between border-t border-border/60 pt-4 text-xs text-muted-foreground">
            <span>演示路线保持公开</span>
            <Link href="/demo/scoping" className="hover:text-foreground">
              进入 demo
            </Link>
          </div>
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
