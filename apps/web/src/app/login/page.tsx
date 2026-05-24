import { StageTwoPlaceholder } from "@/components/layout/stage-two-placeholder";

export default function LoginPage() {
  return (
    <StageTwoPlaceholder
      label="登录"
      blurb="邮箱验证码登录页。Stage 2 接入 /api/auth/send-code 与 /api/auth/verify 两个端点；JWT 落 httpOnly cookie。"
      backHref="/tasks/new"
      backLabel="先体验 demo"
    />
  );
}
