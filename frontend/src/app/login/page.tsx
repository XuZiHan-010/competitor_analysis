import { StageTwoPlaceholder } from "@/components/layout/stage-two-placeholder";

export default function LoginPage() {
  return (
    <StageTwoPlaceholder
      labelKey="loginTitle"
      blurbKey="loginBlurb"
      backHref="/tasks/new"
      backLabelKey="loginBack"
    />
  );
}
