import { StageTwoPlaceholder } from "@/components/layout/stage-two-placeholder";

export default function ReportPage() {
  return (
    <StageTwoPlaceholder
      label="竞品分析报告"
      blurb="报告查看页。Stage 2 将按 TaskScopeContract 的章节顺序动态渲染：核心 4 章走固定模板（功能矩阵、定价表、画像卡片、SWOT 网格），扩展章节渲染 ExtensionFinding。每条结论旁有溯源图标，点开侧滑面板看原文片段与 URL。"
    />
  );
}
