import { StageTwoPlaceholder } from "@/components/layout/stage-two-placeholder";

export default function TaskRunPage() {
  return (
    <StageTwoPlaceholder
      label="DAG 实时可视化"
      blurb="任务运行页。Stage 2 将在这里渲染 4 Agent 的实时进度、节点状态、Trace 日志、以及反馈闭环触发情况。数据源走 SSE 长连接，配合 React Flow 做拓扑展示。"
    />
  );
}
