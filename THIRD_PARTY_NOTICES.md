# Third-Party Notices

本项目（AI 驱动的竞品分析 Agent 协作系统）在运行时工程层借鉴了以下开源项目的设计思路与少量实现。所有借鉴均遵守对应许可证条款；本文件保留原始版权声明，明确借鉴范围，并列出对应的项目落地位置。

---

## DeerFlow (ByteDance)

- **项目地址**：https://github.com/bytedance/deerflow
- **许可证**：MIT License
- **借鉴定位**：**运行时工程能力**（SSE、Worker、Tool 错误处理、Trace 装饰器等），**不借产品主架构**（DeerFlow 是开放式 Deep Research 的单 Lead Agent + middleware + tool loop 模式，与本项目结构化竞品分析的 4 Agent DAG + Pydantic State 正交）
- **借鉴分析详见**：[plans/2026-05-26-deerflow-architecture-inspirations.md](plans/2026-05-26-deerflow-architecture-inspirations.md)

### 借鉴范围（落地至 PRD §五.Y 与本项目 `backend/services/`）

| DeerFlow 模块 | 本项目落地位置 | PRD 锚点 |
|--------------|--------------|---------|
| `runtime/stream_bridge/base.py` | `backend/services/streaming/bridge.py` | §五.Y 约束 4 + §十一-ter 设计钩子 6 |
| `frontend/src/core/threads/hooks.ts`（SSE 心跳 + Last-Event-ID 重连） | `frontend/src/hooks/useTaskStream.ts` | §五.Y 约束 1 + §十二 SSE 风险行 |
| `ToolErrorHandlingMiddleware` | `backend/services/agents/wrappers.py` | §五.Y 约束 2 |
| `runtime/runs/`（RunRecord 生命周期） | `backend/services/runs/manager.py` + `task_runs` 表 | §五.Y 约束 5 + §十 数据库 schema |
| 14 层 middleware 中的 trace 装饰器思路 | `backend/services/agents/decorators.py`（仅取 trace 一层） | §五.Y 约束 3 |
| `subagents/executor.py`（asyncio.gather + timeout） | `backend/services/agents/nodes/collector.py` 内联使用 | §六 5.1 v1.9 并行采集约束 |
| `agents/memory/message_processing.py`（修正信号检测 + 消息过滤） | `backend/services/agents/signals.py` + `state_compaction.py` | §六 5.4 v1.9 correction_detected 信号 |

### 不借鉴的部分

- 单 Lead Agent + 14 层 middleware 主架构（与本项目 DAG 节点边界冲突）
- markdown citation 字符串方案（本项目用强结构化 `source_ids[] → SourceCitation`）
- DAG 内 `ask_clarification` interrupt（本项目用 pre-DAG `ScopingAgent` 替代）
- MCP / Skill / Sandbox 子系统（本项目 tool 列表固定，无需动态加载或代码执行环境）
- 完整 Memory 系统（LLM 驱动自适应摘要、JSON 文件存储、跨 thread 用户偏好画像）

### 原始版权声明

下方文字摘抄自 DeerFlow 项目根 `LICENSE` 文件（2026-05-27 取自 `D:\deerflow\LICENSE`）：

```
MIT License

Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
Copyright (c) 2025-2026 DeerFlow Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 维护规则

- 任何新增对 DeerFlow 或其他开源项目的代码 / 设计借鉴，必须在本文件追加条目（模块路径 + 本项目落地位置 + PRD 锚点）
- 若复制 ≥ 10 行**实质代码**，在对应 `backend/services/...` 文件开头加 `# Adapted from DeerFlow (MIT) — see THIRD_PARTY_NOTICES.md` 注释
- 若改编代码后修改 ≥ 50%，仍需保留 attribution 但可标注 "heavily modified"
