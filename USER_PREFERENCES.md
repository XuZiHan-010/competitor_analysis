# User Preferences

> 本文件记录项目负责人对 AI Agent 的长期协作偏好。所有 Agent 在新对话开始时应先读取本文件，并优先遵守这些偏好；如与更高优先级的系统 / 安全 / 仓库规则冲突，以更高优先级规则为准。

## 1. 回答语言

所有回答必须使用中文。

## 2. 执行方案与 Plan 文件

如果用户要求给出执行方案、plan、计划、方案设计或任务拆解，Agent 应生成 plan 文件并放到 `plans/` 目录，不要直接修改代码。

Plan 文件命名建议：

```text
YYYY-MM-DD-<topic>.md
```

## 3. GitHub 提交偏好

用户没有明确要求提交到 GitHub 时，Agent 不要主动 commit、push 或创建 PR。

当用户说“commit”时，含义是：把当前改动提交并通过 GitHub PR 流程提交到远程，而不是只在本地创建 commit。
