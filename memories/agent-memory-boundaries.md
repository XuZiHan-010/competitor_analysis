---
name: agent-memory-boundaries
description: 区分长期记忆、运行状态、trace、业务状态和项目事实源
type: reference
---

# Agent Memory Boundaries

## 各类状态的职责

| 载体 | 用途 | 更新者 |
|---|---|---|
| `MEMORY.md` | 长期记忆索引，帮助开发 Agent 快速找到稳定经验 | 开发者 / AI 编程 Agent |
| `memories/*.md` | 少量长期有效的协作经验、设计决策和交接提醒 | 开发者 / AI 编程 Agent |
| `WorkflowState` | 单次业务任务的 LangGraph 运行状态 | 后端工作流 |
| `agent_traces` | Agent 节点执行记录、输入输出摘要、成本和延迟 | 后端服务 |
| `agent-states/*.json` | 被构建的业务 Agent 运行状态草案，不是开发 Agent 的 memory | 业务 Agent 系统 |
| `docs/PRD.md` | 产品需求、Schema、API、验收标准事实源 | 项目文档维护者 |
| `claude-progress.txt` | 开发进度日志和里程碑记录 | 项目维护者 |

## 不要混用

- 不要把单次任务状态写进 `MEMORY.md`。
- 不要让业务 Agent 通过 markdown memory 互相传递任务载荷。
- 不要让 memory 替代 Pydantic State、数据库、trace 或 PRD。
- 不要把可从代码直接读取的细节复制到 memory 中长期保存。

## 推荐用法

- 新会话：读 `AGENTS.md`、`MEMORY.md`、`USER_PREFERENCES.md` 和进度日志摘要。
- 开发 Agent：用 memory 找入口，用代码和 docs 验证事实。
- 业务 Agent：继续通过 `WorkflowState` 和数据库传递结构化状态。
- 面试/答辩：用 memory 快速回忆设计取舍，再回 PRD 和代码引用细节。
