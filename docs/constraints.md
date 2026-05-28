# 核心约束

> 本文件列出 **所有 AI 编程 Agent 在本项目中必须遵守的硬性约束**。
> 这些约束直接映射比赛评分标准，违反 = 扣分。

---

## 禁止事项

### ❌ 1. 不要让 Agent 之间用自然语言对话传消息

所有 Agent 间通信必须通过 LangGraph State 的 Pydantic 字段传递。
**理由**：评分项"结构化消息传递 / function calling"的硬要求（35% 权重）。
**对照**：[docs/PRD.md](PRD.md) §6 "Agent 间通信协议"。

### ❌ 2. 不要让任何报告结论无引用

Writer Agent 输出的每条结论（功能描述、SWOT 项、定价说明、画像评价）都必须带 `source_ids`，指向 `SourceCitation`。
**理由**：评分项"信息溯源完整 / 可一键跳转"（35% 权重） + 幻觉抑制（25% 权重）。
**对照**：[docs/PRD.md](PRD.md) §7.6 "溯源单元"。

### ❌ 3. 不要私自降级框架

LangGraph 是题目明确考察点，不可替换为简单的顺序调用或自己写状态机。
**理由**：评分项"编排框架（LangGraph / CrewAI）使用合理"。

### ❌ 4. 不要忽略 robots.txt

CollectorAgent 抓取任何网页前必须检查 robots.txt。被禁的 URL 跳过。
**理由**：评分项"信息采集合规"（10% 权重明确要求）。

### ❌ 5. 不要为不存在的并发问题过度设计

MVP 阶段单用户 / 低并发，架构留扩展口子即可，不要：
- 提前引入 Kafka / RabbitMQ
- 提前做读写分离
- 提前做多副本部署

**对照**：[docs/PRD.md](PRD.md) §5 关于"高并发"的讨论。

### ❌ 6. 不要硬编码任何密钥

所有 API key / 数据库密码 / JWT secret 走环境变量。
**理由**：见 [security.md](security.md)（安全红线）。

---

## 必须事项

### ✅ 1. 输出严格符合 Schema

功能树 / 定价模型 / 用户画像 / SWOT 的字段名和类型 **不可** 随意改。
**对照**：[docs/PRD.md](PRD.md) §7 完整 Schema 定义。
**验收**：字段完整率 ≥95%。

### ✅ 2. 每个 Agent 节点都要写 Trace

每个 LangGraph 节点执行时必须记录到 `agent_traces` 表，字段含：
- `prompt`
- `input_payload`
- `output_payload`
- `tokens_in` / `tokens_out` / `cost_usd`
- `latency_ms`
- `langsmith_run_id`（关联 LangSmith trace，可空）
- `decision_meta`（决策摘要，如"为何打回"）

**理由**：评分项"可观测性达标"（25% 权重，明确要求 Token 消耗可查）。完整定义见 [PRD §五.Y](PRD.md) 约束 3/6 与 §十 `agent_traces` 表。

### ✅ 3. 反馈闭环要能真实触发

QA Agent 必须能识别问题并打回上游 Agent，且重跑后输出有改善。
**禁止伪闭环**：QA 永远 pass，或重跑不改善，会被评委识破扣分。
**对照**：[docs/PRD.md](PRD.md) §6 Agent 4 "反馈闭环逻辑"。

### ✅ 4. 每条结论可一键溯源

前端报告渲染时，所有 `source_ids` 转成可点击图标，点开看原始 URL + 抓取片段。

### ✅ 5. 遵守 PRD 优先级

- **P0**：必须完成（见 [docs/PRD.md](PRD.md) §11）
- **P1**：答辩前必须完成；允许压缩样本量 / 展示深度，不允许取消能力
- **P2**：不在 MVP 范围，禁止提前实现

---

## 评分项与本约束的映射

| 评分项 | 权重 | 对应约束 |
|---|---|---|
| 多 Agent 协作与输出可信度 | 35% | 禁止-1, 禁止-2, 必须-1, 必须-3, 必须-4 |
| 技术深度与工程完整度 | 25% | 禁止-3, 禁止-5, 必须-2 |
| 业务价值与产品体验 | 20% | 必须-1, 必须-5 |
| 代码质量与文档 | 10% | 见 [code-style.md](code-style.md) + [git-conventions.md](git-conventions.md) |
| 合规、材料与答辩 | 10% | 禁止-4, 禁止-6 + [security.md](security.md) |
