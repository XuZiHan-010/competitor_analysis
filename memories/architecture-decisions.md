---
name: architecture-decisions
description: 项目长期有效的 Agent 与全栈架构设计决策
type: project
---

# Architecture Decisions

## LangGraph 是主编排框架

本项目不是简单顺序调用，而是长任务、多节点、有状态、可重试的 Agent 工作流。LangGraph 承担 DAG 编排、条件边、checkpoint 和状态流转。

关键入口：

- `backend/graph/workflow.py`
- `backend/graph/state.py`

## Agent 间通信必须走 Pydantic State

Agent 之间不能用自然语言散文传消息。所有跨 Agent 载荷都必须进入强 Schema 的 `WorkflowState` 或相关 Pydantic 模型。

这条设计同时服务于：

- 比赛评分中的结构化消息传递。
- Schema 校验和可测试性。
- 后续替换模型供应商时保持业务协议稳定。

## QA 在 Writer 之前

真实执行顺序是：

```text
ScopingAgent -> collect -> analyze -> qa_check -> write
```

QA 在 Writer 之前拦截数据不足、引用缺失和核心 Schema 缺口。这样可以避免 Writer 在证据不足时消耗大量成本生成低质量报告。

## 强溯源是报告可信度基础

报告结论必须能关联到 `SourceCitation`。可信度不靠 LangSmith 替代，而靠：

- `source_ids`
- `ReportClaim`
- QA 检查
- 前端溯源面板

## Provider fallback 是采集可靠性的核心

搜索与外部数据采集采用 Provider 模式，Collector 只依赖抽象能力，不关心底层服务。主层和兜底层的组合用于提升召回、控制额度并降低单点失败影响。

相关入口：

- `backend/services/search/hybrid.py`
- `backend/services/search/providers.py`
- `backend/services/scraper.py`

## Demo 与真实路径必须隔离

Demo 路由用于稳定演示，真实任务路径必须根据用户输入动态生成，不允许回退到 demo fixture。这是保证业务价值和多 Agent 可信度的关键边界。
