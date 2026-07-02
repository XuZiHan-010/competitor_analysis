# MEMORY.md

> 本文件是项目的长期记忆索引，帮助新接手的 AI Agent 或开发者快速找到稳定经验、协作偏好和关键决策。
>
> 它不是项目事实源。涉及功能、Schema、部署状态、测试结果或代码实现时，必须回到当前仓库、PRD、架构文档和进度日志核验。

---

## 使用规则

- 先读 [AGENTS.md](AGENTS.md) 了解必须遵守的规则，再读本文件了解长期记忆入口。
- 本文件只放索引和稳定判断，不记录单次任务流水。
- 任何可能过期的信息都要回源验证，尤其是项目进度、部署状态和代码路径。
- 不在 memory 文件中写真实密钥、平台凭据、数据库地址或任何可用于访问生产服务的信息。
- `agent-states/` 是被构建的业务 Agent 运行状态，不是 Codex / Claude 的长期 memory。

---

## 必读事实源

| 入口 | 作用 |
|---|---|
| [USER_PREFERENCES.md](USER_PREFERENCES.md) | 项目负责人长期协作偏好，语言、plan 路径、GitHub 提交语义以此为准 |
| [claude-progress.txt](claude-progress.txt) | 项目进度日志，接手前读取顶部摘要确认当前状态 |
| [docs/PRD.md](docs/PRD.md) | 产品需求、Agent 协议、Schema、API 与验收标准的唯一事实源 |
| [docs/architecture.md](docs/architecture.md) | 系统分层架构与多 Agent DAG 的轻量入口 |
| [docs/constraints.md](docs/constraints.md) | Agent 开发硬约束：结构化通信、强溯源、反馈闭环等 |
| [docs/deployment.md](docs/deployment.md) | Railway、Neon、Upstash、LangSmith 的部署说明 |

---

## 长期记忆条目

| Memory | 类型 | 说明 |
|---|---|---|
| [project-status](memories/project-status.md) | project | 当前阶段、最大缺口、进度日志读取规则 |
| [architecture-decisions](memories/architecture-decisions.md) | project | LangGraph、Pydantic State、QA before Writer、强溯源与 Provider fallback 等长期设计决策 |
| [agent-memory-boundaries](memories/agent-memory-boundaries.md) | reference | 区分 `MEMORY.md`、`WorkflowState`、`agent_traces`、`agent-states/`、PRD/docs 的职责 |
| [deployment-and-ops](memories/deployment-and-ops.md) | reference | 线上部署、运行排障与安全边界的长期记忆 |
| [recurring-feedback](memories/recurring-feedback.md) | feedback | 用户反复强调的协作偏好和交付标准 |

---

## 维护原则

- 只新增长期有效的经验；临时任务计划放 [plans/](plans/)。
- 代码事实变化时，优先更新对应 `docs/` 或 PRD，再按需更新 memory 摘要。
- 进度变化优先更新 [claude-progress.txt](claude-progress.txt)，本文件只保留“到哪里查”的索引。
- 如果 memory 与代码或 PRD 冲突，以代码和 PRD 为准，并修正 memory。
