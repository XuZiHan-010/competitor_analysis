---
name: project-status
description: 当前项目阶段、最大缺口与进度日志读取规则
type: project
---

# Project Status

## 稳定摘要

本项目是 AI 驱动的竞品分析多 Agent 全栈系统。代码层面后端与前端主链路已经基本落地，前后端已部署到 Railway，核心能力包括对话式立项、多 Agent DAG、报告生成、溯源、导出、账号隔离、SSE 进度和 LangSmith 可观测。

## 接手时必须确认

- 每次新会话先读 [claude-progress.txt](../claude-progress.txt) 顶部摘要。
- 进度日志中的“最后更新”和“系统状态”比本 memory 更新更可信。
- 若涉及真实线上状态、最新缺口或已完成修复，必须回到进度日志、代码和部署文档核验。

## 当前长期风险

- 真实 API 全链路 3 竞品跑批仍是最需要优先确认的验收缺口。
- Agent 输出质量依赖采集、来源相关性、Schema 完整性、QA blocker 和 Writer 渲染的整条链路，排查时不能只看单个 Agent。
- 前端与后端已分别部署，任何线上问题都要分清是前端请求、API、Agent 执行、外部服务、数据库还是 Redis 事件流。

## 接手建议

新 Agent 或新人开发者不要从随机文件开始读。推荐顺序：

1. [AGENTS.md](../AGENTS.md)
2. [MEMORY.md](../MEMORY.md)
3. [claude-progress.txt](../claude-progress.txt) 顶部摘要
4. [docs/architecture.md](../docs/architecture.md)
5. 与当前任务相关的 PRD / docs / 代码入口
