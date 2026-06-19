# PRD: AI 驱动的竞品分析 Agent 协作系统

> **文档性质**: 产品需求文档（PRD），交付给开发 Agent 拆任务用
> **状态**: active —— 当前真实事实源，版本演进交给 git log
> **当前版本**: v2.0（2026-05-28）
> **作者**: PM (Claude) + 项目负责人 Eric
>
> **维护约定**：PRD 是单点事实源（[AGENTS.md](../AGENTS.md) §五.1）。任何改动直接更新本文档对应章节，**不**在头部堆 changelog；版本演进通过 `git log docs/PRD.md` 查看。重大设计决策的来龙去脉沉淀在 [plans/](../plans/) 下的 dated 设计文档（如 [2026-05-23-dynamic-outline-scoping-design.md](../plans/2026-05-23-dynamic-outline-scoping-design.md)、[2026-05-26-deerflow-architecture-inspirations.md](../plans/2026-05-26-deerflow-architecture-inspirations.md)）。

---

## 一、Context / 项目背景

### 为什么做这个

企业产品/战略团队做竞品分析时，重复经历"搜集 → 对比 → 评价整理 → SWOT → 报告"五个环节，痛点：
1. **信息源分散**：官网、应用商店、社媒、行业报告分散在 5+ 渠道
2. **结构不统一**：每个分析师的报告框架不同，难以横向对比
3. **依赖人工经验**：分析质量取决于分析师的行业认知和方法论
4. **难以追溯**：结论与原始数据的关联在 Word/PPT 中容易丢失

### 这个项目要做什么

实现一个 **多 Agent 协作的竞品分析系统**，模拟"数字调研小组"——4 个专职 Agent（采集 / 分析 / 撰写 / 质检）通过结构化消息协作，从产品/竞品名输入到结构化报告输出全自动完成，并通过 **反馈闭环** 自我校验。

### 预期成果

- 一个可外部访问的 Web 产品（Railway 部署）
- 输入"目标产品 + 竞品列表"→ 5-10 分钟内产出可信、可溯源的结构化竞品报告
- 报告支持网页交互、PDF 离线、PPTX 汇报三种形态

---

## 二、目标用户与典型场景

### 主用户：企业产品经理 / 战略决策者

**画像 A：互联网/SaaS 产品经理（小明）**
- 接到新版本规划任务，需要 1-2 天内摸清 3-5 个竞品的功能/定价/口碑
- 当前方式：自己 Google + 试用产品 + 整理 Excel
- 痛点：信息覆盖不全；功能对比维度自己拍脑袋；老板问"这个结论哪来的"答不上来

**画像 B：传统行业战略部（小红，汉高战略部实习生场景）**
- 接到管理层 Brief：评估某新兴品类在国内的竞争格局
- 当前方式：买行业报告（贵且滞后） + 桌面研究 + 给老板写 PPT
- 痛点：行业报告样本少；自己研究效率低；结构化输出耗时长

### 共同诉求
1. **结构化**：报告字段固定，跨竞品可横向对比
2. **可信**：每个结论可点击溯源到原始网页/评论
3. **可介入**：发现 Agent 结论有问题，能手动修正而不是全部推倒
4. **可汇报**：PDF 给客户、PPTX 给老板

### 待验证场景（与汉高战略部实习生访谈）
- 真实工作流中，"竞品列表"是用户自己定的还是要系统推荐的？
- 哪些字段是必须的？（建议带着我们的 Schema 草案去访谈）
- 报告交付物的真实形态？（HTML/PDF/PPTX 哪个用得最多）

---

## 三、核心价值主张（评分映射）

| 价值 | 量化指标 | 对应评分项 |
|---|---|---|
| **效率提升** | 5-10 分钟出报告 vs 人工 1-2 天 | 业务价值（20%） |
| **覆盖度提升** | 自动覆盖 ≥5 信息源（官网+搜索+应用商店+评论+社媒） | 业务价值（20%） |
| **一致性** | 100% 输出符合预定义 Schema | 多 Agent 协作（35%） |
| **可信度** | 每条结论可一键溯源到原始 URL | 多 Agent 协作（35%） |
| **可介入** | 用户可手动修正 Schema 字段，触发重跑 | 业务价值（20%） |

---

## 四、核心用户流程

### 主流程（P0，MVP 必须）

```
[1] 用户登录（demo 一键直登，未来可扩展 OAuth）
    ↓
[2] 新建分析任务（任务创建页 /tasks/new）：
    **唯一输入：单一 NL 文本框**——不再提供独立的竞品 chip 输入区，
    已知竞品名由 ScopingAgent 从 NL 中提取（用户后续可在 [3] 立项页增删）。
    ScopingAgent 自动识别 3 种意图：
      A. 列表式：「对比 SK-II / 资生堂 / 雅诗兰黛，重点看会员体系」
                 → AI 提取 + 推荐 2-3 个同价位竞品 + 生成大纲
      B. 意图式：「分析中国高端护肤品牌在 KOL 营销和会员体系的差异」
                 → AI 推荐 3-5 个竞品 + 把研究意图拆解成大纲
      C. 混合式：「我知道 SK-II 和雅诗兰黛，还有谁也在这个价位？」
                 → AI 提取已知 + 补全到 3-5 个 + 大纲
    页面提供 3 个**示例 brief 快填 chip**（如 "Trae · AI 编程"、
    "飞书 · 企业协作"、"抖音 · 内容电商"），点击仅一键填充 NL 文本框，
    **不是竞品输入**——评委首次到访可零成本看到一份合规的 NL 写法。
    提交动作有两种分支：
      • 默认 →「生成研究计划」按钮 → 调 ScopingAgent → 进入 [3] 立项页
      • **direct 模式**：NL 中含「直接生成 / 直接分析 / 跳过 / 不要大纲」
        等关键词（中英双语词典）→ 按钮文案切换为「直接分析」→
        跳过 [3] 立项页，直接进入分析（MVP 阶段路由到 `/demo/scoping`
        预录路径回放；后端就绪后接真实 DAG，仍跳过 scoping）。
    ↓
[3] 对话式立项（scoping 页 /tasks/new/scoping）：
    ScopingAgent（见 §六 5.0）一次响应同时返回：
      (a) 竞品列表 = NL 提取 ∪ 手动 chip ∪ AI 推荐，最终保证 3-5 个
          每个竞品带 source 标签（user_chip / nl_extracted / ai_recommended）
          AI 推荐的 chip 带「✨ 推荐理由」hover tooltip，用户可踢掉
      (b) 初步大纲（核心 4 章 🔒 + N 项扩展章节 ✏️，每章带「意图描述」）
      (c) **用户研究计划（方案 C）**：问卷/访谈提纲草案 + 启用开关（`UserResearchPlan`，§7.0）
      (d) 1-3 个补充澄清问题（可跳过）
      (e) intent_mode 标签 + rationale 摘要（顶部折叠面板，默认收起）
    研究计划各模块（竞品列表 / 分析维度 / 用户研究计划 / 输出结构）以**可折叠卡片**呈现，展开可编辑、收起更简洁（§九）
    用户编辑：
      - 竞品 chip：可增删（包括踢掉 AI 推荐的），可点「让 AI 再推荐几个」补
      - 核心章节（🔒 功能树 / 定价模型 / 用户画像 / SWOT）可改名 / 改意图 / 调顺序，不可删
      - 扩展章节（✏️ 任务相关维度）可改名 / 改意图 / 调顺序 / 删除 / 自定义新增
      - **用户研究计划**：开关启用/不启用；可编辑问卷题目；可选上传真实问卷结果 / 访谈记录（→ 一手数据，§八上传端点）
      - 「重新生成大纲」按钮 = 带当前编辑过的章节 + 竞品 + 澄清回答回到 ScopingAgent 再生成
    用户点「确认 → 开始分析」时，大纲 + 用户研究计划 freeze 成 TaskScopeContract（见 §七 7.0）

    ⚠️ 路由职责边界（详见 §十一-quater 11Q.7）：本页**仅**渲染
    ScopingAgent 真实产物；ScopingAgent 未接通时降级为"4 核心 + 空扩展 + 空
    竞品 + 连线中提示"骨架，绝不回退到任何与领域绑定的硬编码 mock，也不读取
    /demo/* fixture——这是为了避免"输入 AI IDE 看到护肤大纲"的演示翻车。
    ↓
[4] 启动 Agent 协作（任务运行页 /tasks/{id}）：
    实时显示 DAG 进度（哪个 Agent 在跑、跑到哪一步、Trace 可点开）
    采集 Agent → 分析 Agent → 质检 Agent → 撰写 Agent
                                  ↓
                （质检不通过，打回采集 Agent 重采，最多 3 次；
                 达标或重试上限后才进撰写 Agent）
    各 Agent 都按 TaskScopeContract 中的维度做事
    ↓
[5] 报告产出（/reports/{id}）：
    网页交互式（默认）+ 可导出 PDF / PPTX
    报告章节顺序、标题、字段范围完全按 TaskScopeContract 渲染
    ↓
[6] 用户介入修正（P1）：
    在网页报告中手动编辑 Schema 字段 → 触发局部重跑
    ↓
[7] 报告归档到"我的报告"
```

### 用户旅程关键体验点

| 节点 | 用户期望 | 设计承诺 |
|---|---|---|
| 等待期 | 不焦虑 | 实时 DAG 可视化 + Agent 当前正在做什么的中文描述 |
| 看报告 | 快速理解 | 顶部摘要 + 功能对比矩阵 + SWOT + 详情可展开 |
| 不信任结论 | 一秒验证 | 每条结论旁有"溯源"小图标，点击展开原始数据片段+URL |
| 想修改 | 不重跑全流程 | 编辑单个字段 → 仅触发涉及该字段的 Agent 重跑 |

---

## 五、系统架构

> **系统架构图（分层架构 + 多 Agent DAG 流转）、分层说明、技术栈与部署拓扑，已抽到独立的 [docs/architecture.md](architecture.md)**——便于按需阅读、也作为比赛交付的架构文档。本节只保留两份被全文交叉引用的事实源表格：§五.Y 运行时约束、§五.X 模型选型。

### 五.Y 运行时可靠性保障

> 本节统一收口长任务运行时的工程约束。**借鉴自 [ByteDance DeerFlow](https://github.com/bytedance/deerflow)（MIT License）**，详见 [plans/2026-05-26-deerflow-architecture-inspirations.md](../plans/2026-05-26-deerflow-architecture-inspirations.md) 与项目根 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

竞品分析任务跑 2-5 分钟很正常（5 竞品 × 多维度抽取 + Survey 4 阶段 + Writer 渲染），网络抖动 / 浏览器 tab 切换 / API 失败 / LLM 死循环都可能让用户中途失去进度。本节定义 5 条**强制**工程实现约束：

| # | 约束 | 实现位置 | 验收 |
|---|------|---------|------|
| 1 | **SSE 心跳 + Last-Event-ID 幂等重连** | `frontend/src/hooks/useTaskStream.ts` + `backend/api/routes/stream.py` | 15s 空闲发 `__heartbeat__`；断线重连传 `Last-Event-ID` 头，服务端从该 event 之后续推 |
| 2 | **Tool Error Wrapper** | `backend/services/agents/wrappers.py` | 所有 Agent 工具调用（`web_search` / `fetch_page` / `SurveyTool` / `app_review_fetch`）统一包装：异常转成 `ToolMessage(error_content)`，不挂掉整个 DAG；写入 `trace_log` `stage="tool.error"` |
| 3 | **@traced_node 装饰器** | `backend/services/agents/decorators.py` | 每个 LangGraph 节点函数挂 `@traced_node`，自动记录 `{stage, prompt_hash, input_summary, output_summary, tokens_in, tokens_out, cost_usd, latency_ms, failure_reason}` 到 `agent_traces` 表，节点代码不手写 trace（`cost_usd` 按 §五.X 模型单价 × token 估算） |
| 4 | **StreamBridge 抽象（producer/consumer 解耦）** | `backend/services/streaming/bridge.py` | 抽象 `publish(run_id, event)` / `subscribe(run_id) → AsyncIterator`；MVP 用内存实现，生产化平滑切 Redis（详见 §十一-ter 设计钩子 6） |
| 5 | **RunRecord 任务生命周期** | `task_runs` 表（详见 §十）+ `backend/services/runs/manager.py` | `{run_id, task_id, status, error, checkpoint_id, started_at, completed_at}`；`checkpoint_id` 与 LangGraph PostgresCheckpointer 的 `thread_id` 一一对应，支持"刷新页面后任务还在跑 + 失败从中断点续跑" |
| 6 | **LangSmith 执行过程 trace 上报（可选增强层）** | LangGraph 原生回调（设 `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` env，key 不入库）；`agent_traces` 写入 `langsmith_run_id` 关联 | env 开关控制（CI 默认关，本地 debug + 答辩演示开）；多 Agent 执行树在 LangSmith 可查、token/cost 仪表盘可见；**SurveyTool 涉敏节点（访谈 / 用户声音 / persona）必须 `hide_inputs`/`hide_outputs` 或 anonymizer 脱敏后再上报**（合规红线，见 [docs/security.md](security.md)） |

**可观测三层分工（不冗余）**：① `agent_traces` 表（自建 Postgres）是事实源，撑产品内可观测页 + 演示断网兜底，带 token/cost；② LangSmith 是开发期 debug + 答辩展示的增强层；③ 报告权威性（每条结论可溯源）靠 `source_ids` + 前端溯源面板（§六 5.3 / §七），**与 LangSmith 正交，不可被其替代**。

**为什么不抄 DeerFlow 全套**：DeerFlow 的 14 层 middleware + MCP + Skill + Sandbox 是为开放式深度研究设计，与我们结构化竞品分析（4 Agent DAG + 强 Schema）正交。本节只取 5 条工程地基，**主架构（PRD §六 多 Agent DAG）不动**。

**比赛评分对应**：本节 1-5 条直接撑起评分卡 25% "技术深度与工程完整度" 的"长任务稳定性"维度；约束 2/3 还为 35% "多 Agent 协作可信度"中的"trace 完整、可追溯"提供工程保障。约束 6（LangSmith）撑 25% 中"每个 Agent 的 Prompt/输入/输出/Token 消耗均有 Trace 可查"，且其涉敏脱敏策略同时撑 10% "合规"中的"问卷 / 访谈数据脱敏"——同一动作覆盖两个维度。注意"信息溯源保证报告权威性"是 35% 的独立要求，靠 `source_ids` 实现，**不靠 LangSmith**。

---

### 五.X 模型选型决策表

按 Agent / task 锁定 LLM 模型，开发期写死在 `backend/settings.py`，不暴露给终端用户切换。

| Agent | 模型 | 输入 / 输出（USD/1M tokens） | 7 天演示成本 | 能力分 | 选择理由 |
|-------|------|----------------------------|-------------|--------|---------|
| CollectorAgent | `gpt-4o-mini` | $0.15 / $0.60 | ~$0.08 | 75 | query 改写任务轻、JSON 输出强约束，便宜款够用；与 Scoping/QA 同模型同 SDK，收敛外部依赖 |
| AnalystAgent | `deepseek-v4-pro` | $0.435 / $0.87 | ~$0.21 | 86 | 推理强 + 384K 输出容量；成本仅 gpt-4.1 的 1/6（2026-05 永久 75% 降价后） |
| WriterAgent | `deepseek-v4-pro` | $0.435 / $0.87 | ~$0.21 | 88（中文） | 中文长报告自然度高；与 AnalystAgent 同模型简化 prompt 协调 |
| QAAgent | `gpt-4o-mini` | $0.15 / $0.60 | ~$0.10 | 75 | JSON 结构化检查任务简单，便宜款够用 |

**演示周（7 天 × 5 任务/天）总成本上限**：~$3（含 20% 缓冲）；单次任务 token 消耗假设 100K input + 20K output。

**选型原则**："成本 × 能力同时兼顾，不追求最强"——例如 Analyst 不用 gpt-4.1（能力 90 / 成本 $1.26），改用 DeepSeek V4 Pro（能力 86 / 成本 $0.21），**用 1/6 的钱买 95% 的能力**。

**为什么不全用 DeepSeek**：CollectorAgent 的 query 改写是轻量 JSON 任务，与 Scoping/QA 一并用 gpt-4o-mini，共用 OpenAI 同源栈、跨家协调成本最低。

**SDK 与配置**：
- DeepSeek 兼容 OpenAI SDK（base_url=`https://api.deepseek.com/v1`），与 gpt-4o-mini 共用 `openai` Python 包
- 环境变量：`OPENAI_API_KEY` / `DEEPSEEK_API_KEY`（密钥管理见 [docs/security.md](security.md)）

**未来路径**：见 §十一-ter 第二阶段「合规」行——MVP 已部分国产化（Analyst+Writer），生产化阶段补充智谱 GLM / 阿里通义 / MiniMax 多 Provider。

---

## 六、多 Agent 设计（核心）

> **架构**：系统总共 5 个 Agent，分两层——
> - **ScopingAgent**（5.0）：在主 DAG 启动**之前**跑，对话式立项的主语，同步 LLM 调用
> - **DAG 内 4 Agent**（5.1-5.4）：Collector / Analyst / QA / Writer，通过 LangGraph 编排，State 驱动 + 反馈闭环
>
> **DAG 执行顺序**（见 §五图 B）：`collect → analyze → qa_check → write`。**QA 在 Writer 之前**——QA 先校验分析数据是否充分，出现 blocker 则打回 Collector 重采（最多 3 次），达标或重试上限后才进 Writer，避免在数据不足时白白消耗 Writer 的 token。下文小节号（5.1-5.4）按 Agent 编号排列，非执行顺序。

### Agent 5.0: 立项 Agent (`ScopingAgent`)

**职责**：对话式立项阶段的主语。负责把用户 NL 转成一份可执行的 TaskScopeContract 草案。

具体工作：
1. 解析用户 NL，识别意图（`list` / `intent` / `mixed`）
2. 提取并推荐竞品，保证最终列表有 3-5 个候选
3. 生成大纲：核心 4 章（固定）+ AI 建议扩展章 ≤ 4 项（按 NL 焦点定制）
4. 生成 1-3 个澄清问题
5. 接收用户编辑反馈（编辑过的章节 / 增删的竞品 / 澄清回答），迭代再生成

**扩展维度数量约束**（写进 prompt + 后端 freeze 时校验）：
- ScopingAgent 单次最多建议 **4 个**扩展维度（`source="ai_suggested"`），避免任务范围发散、控制延迟与成本
- 用户在大纲页 [✎] 手动添加的扩展维度（`source="user_added"`）**不受此上限**——把"可控规模"和"用户自由度"分离

**与 DAG 内 4 Agent 的关键差别**：

| 维度 | ScopingAgent | DAG 4 Agent |
|---|---|---|
| 调用位置 | 主 DAG **之前**（用户在 scoping 页面时） | 主 DAG **之内**（用户点「确认 → 开始分析」之后） |
| 调用形态 | 同步 LLM call，前端等 1-3s | 异步 LangGraph 编排，SSE 推送进度 |
| 反馈闭环 | 无 QA 闭环，用户本人即 reviewer，编辑即修正 | QA Agent 自动检查 + 打回重做（最多 3 次） |
| 输出 | `ScopingDraft` → 用户 freeze 后 → `TaskScopeContract` | `WorkflowState` 各 Agent 产物 |
| 是否进 trace_log | 进 `scoping_drafts` 表（独立） | 进 `agent_traces` 表 |

**意图识别规则**（LLM prompt 里写死）：

| 意图 | 触发条件 | ScopingAgent 行为重点 |
|---|---|---|
| `list` | NL 主要由 2+ 个具体竞品名构成 | 提取所有提到的竞品，推荐 2-3 个**同价位 / 同目标人群**的额外候选；大纲基于"对比"目的生成 |
| `intent` | NL 描述研究问题但未提具体竞品（或只提 1 个） | **AI 推荐 3-5 个竞品**，附 reason（同价位 / 同渠道 / 同目标人群）；大纲对研究问题做精细拆解 |
| `mixed` | NL 有 1-2 个竞品名 + 显式的"还有谁"诉求 | 提取已知竞品 + 补全到 3-5 个 AI 推荐 + 标准大纲 |

**输入 Schema** (`ScopingRequest`):
```python
class ScopingRequest(BaseModel):
    user_brief: str                                       # NL 全文
    known_competitors: list[str] = []                     # 已知竞品名（来源见下）
    previous_draft: ScopingDraft | None = None            # 「重新生成大纲」时回带
    clarification_answers: dict[str, str] = {}            # 上一轮澄清问题的答复
```

**`known_competitors` 来源说明**：
- **首次调用**（从 `/tasks/new` 提交）：始终为空数组 `[]`——`/tasks/new` 不提供独立的竞品 chip 输入区，已知竞品名由 ScopingAgent 自己从 `user_brief` 中提取
- **重新生成大纲调用**（从 `/tasks/new/scoping` 立项页提交）：携带用户在立项页手动**增删**后的竞品名列表，确保再生成时不丢用户已确认的竞品
- 字段保留向后兼容：若未来恢复"任务创建页竞品 chip 输入"或第三方调用需要预填，仍可走此字段

**输出 Schema** (`ScopingDraft`):
```python
class CompetitorCandidate(BaseModel):
    name: str
    source: Literal["user_chip", "nl_extracted", "ai_recommended"]
    reason: str | None    # AI 推荐时填理由：同价位 / 同目标人群 / 同渠道 / 同品类领头

class ScopingDraft(BaseModel):
    intent_mode: Literal["list", "intent", "mixed"]
    competitors: list[CompetitorCandidate]                # 保证 3-5 个
    dimensions: list[DimensionSpec]                       # 核心 4 + N 扩展
    user_research_plan: UserResearchPlan | None           # 用户研究模块草案（方案 C）：含可编辑问卷 + 启用开关；§7.0
    clarifying_questions: list[ClarifyingQuestion]
    rationale: str                                        # AI 拆解依据，留 trace + 可选展示
```

**对下游的承诺**：
- `competitors` 长度 ∈ [3, 5]——少于 3 时 ScopingAgent 必须用 AI 推荐补齐
- `dimensions` 中 `layer="core"` 的恰好 4 项（功能树 / 定价 / 画像 / SWOT），不可缺失，可改名
- `dimensions` 中 `source="ai_suggested"` 的条目 ≤ 4——`source="user_added"` 不计入此上限
- 输出**幂等**——同样的输入两次调用应给出**结构相同**（顺序可不同）的草案，方便用户多次「重新生成」时不大幅震荡

### Agent 5.1: 采集 Agent (`CollectorAgent`)

**使用模型**：`gpt-4o-mini`（query 改写任务轻、JSON 输出强约束，便宜款够用；与 Scoping/QA 同模型同 SDK；详见 §五.X 选型决策）

**职责**: 把"产品/竞品名"变成结构化原始数据

**工具集**:
- `web_search(query, max_results=5)` — **HybridSearch Provider 模式**，对 CollectorAgent 透明（一句调用，拿到 `list[SourceCitation]`）；内部实现：
  - `SearchProvider` Protocol 抽象：`TavilyProvider`（主）→ `SerpApiProvider`（备）
  - **降级策略**：Tavily 失败（429 / timeout / 500 / 空结果）→ 自动切换 SerpApi，每次降级写入 `trace_log`（`stage="search.fallback"`）
  - **全失败**：抛 `SearchUnavailableError`，LangGraph CollectorAgent 节点走 retry（最多 3 次）
  - **启动时探测**：按 `TAVILY_API_KEY` / `SERPAPI_API_KEY` 可用性自动构建 provider 顺序；无任何 key 时明确报错
  - 返回的每条 `SourceCitation` 含 `provider` 字段（记录实际使用的 provider 实现名）
  - 代码路径：`backend/services/search/`（`providers/base.py` / `providers/tavily.py` / `providers/serpapi.py` / `hybrid.py`）
- `fetch_page(url)` / `fetch_pages(urls)` — Playwright 抓取。**单浏览器复用 + 有界并发**：一次采集只启动一个 Chromium 实例，所有 URL 经同一 browser 并发抓取（`asyncio.Semaphore` 限流），单页 8s goto 超时 + 12s 总预算；导航失败（如 `net::ERR_ABORTED`）只记 `skip_reason="fetch_error"` 不做二次兜底。**抓取失败/被 robots 拒绝时保留搜索阶段返回的原始 `SourceCitation`（含 snippet）而非丢弃**，避免把竞品来源数压到 QA `≥5` 门槛以下导致假闭环重采
- `app_review_fetch(app_name)` — 应用商店评论真实抓取（P1 答辩前必达）：优先抓 App Store / Google Play / Product Hunt 等公开评论；失败时降级到 `web_search` 用户反馈或 `ai_simulated` 兜底，必须在 `SourceCitation.type/source_type/provider` 中明确标识真实来源或模拟来源
- `SurveyTool(competitor, dimension_intent, collected_sources, user_research_plan)` — 用户研究子工作流（方案 C 混合），四层级联：
  1. **Stage 1**：AI 设计问卷 / 访谈提纲（`questionnaire_designer`，5-10 道题）；**用户可在 scoping 阶段编辑题目**（题目来自 `TaskScopeContract.user_research_plan.questionnaire`，访谈提纲=问卷的一种形态）
  2. **Stage 2**：检索公开调研数据（`existing_survey_finder` → `published_survey`）+ 复用已采集用户评论（`user_voice_collector` → `public_review`）
  3. **Stage 3**：推断目标画像（`persona_inferrer`）→ 收集答卷，**数据来源三层优先级（方案 C）**：
     - ① **一手（最高可信）**：若用户上传真实问卷结果 / 访谈记录 → 解析为 `user_uploaded_primary`（见 §八 上传端点；上传即脱敏）
     - ② **公开二手**：Stage 2 的 `published_survey` / `public_review`
     - ③ **模拟兜底**：无上传时 `SurveyDistributor.distribute()`（MVP `SimulatedDistributor`，LLM 模拟作答，**显式标注 `ai_simulated` + ⚠️示例/Demo 用**）
  4. **Stage 4**：洞察归纳（`insight_aggregator`），强制溯源，整合三层证据，喂入 用户画像/痛点/满意度/SWOT，产出 `SurveyResult`
  
  每个 Stage 出口写入 `trace_log`（命名约定见 §六 WorkflowState 注）；合规抓取走主线 `fetch_page` 策略，robots 拒绝域名进 `skipped_urls`；`user_research_plan.enabled=False` 时整个 SurveyTool 跳过。

**并行采集约束**：5 个竞品的 `web_search` + `fetch_page` 走 `asyncio.gather` 节点内并行（**P0 性能必需**，串行 5 × 30s 演示卡 2.5 分钟）；竞品内多维度 `web_search` 亦并发；每个竞品采集任务带 60s timeout + 单点失败隔离（一个竞品挂不拖累其他）。代码位置：`backend/services/agents/nodes/collector.py`。所有 tool 调用走 §五.Y 约束 2 的统一 wrapper，错误不挂掉 DAG。

**LLM 瞬时错误退避**：`LLMClient` 对所有 provider 调用（OpenAI / DeepSeek）统一加**指数退避重试**（仅瞬时错误 429/503/超时/连接中断，最多 3 次）+ 单次调用超时上限，避免高峰期 503 直接把节点打成降级兜底。非瞬时错误（如 400）立即抛出不重试。代码位置：`backend/services/llm/client.py`（`_call_with_retries` / `_is_transient`）。

**输入 Schema**:
```json
{
  "scope_contract": "TaskScopeContract"  // 完整传入，Collector 自己从中派生 dimensions_required
}
```

**行为约定**：
- 不接收硬编码的 `dimensions_required: ["features", "pricing", ...]`
- 从 `scope_contract.dimensions` 派生采集计划：核心层维度 → 跑预设搜索模板；扩展层维度 → 用 `dimension.intent` 做 query 改写（例："重点看会员体系" → 搜索 `<竞品名> 会员体系 黑卡` `<竞品名> 折扣节奏`）
- **领域上下文消歧**：从 `scope_contract.user_brief` 提取简短领域关键词（`domain_context`），拼接到每条静态 query 末尾，并在 LLM query 改写的 prompt 中明确指示"竞品名可能有歧义，需用分析领域消歧+加产品类目限定词"。解决 `Trae`（易混淆球星名）、`Cursor`（通用 UI 术语）等歧义品牌在裸名搜索下命中率极低的问题。代码：`_domain_context()` + `_build_dimension_queries(domain_context=)` + `_rewrite_queries(domain_context=)`
- 输出 `RawCollectionResult` 中的 sources 增加 `dimension_id` tag，便于 Analyst 路由

**输出 Schema** (`RawCollectionResult`):
```json
{
  "competitor": "string",
  "sources": [
    {
      "type": "official_site | search | app_store_review | published_survey | public_review | ai_simulated",
      "url": "string",
      "title": "string",
      "snippet": "string",
      "fetched_at": "ISO8601",
      "raw_content": "string"
    }
  ],
  "completeness_score": "0-1"  // 自评，给质检 Agent 用
}
```

### Agent 5.2: 分析 Agent (`AnalystAgent`)

**使用模型**：`deepseek-v4-pro`（推理能力 86 分 + 384K 输出容量足够 4 维度+SWOT 综合；成本仅为 gpt-4.1 的约 1/6；详见 §五.X 选型决策）

**职责**: 把原始数据结构化为竞品知识 Schema

**核心动作（按维度路由）**:

对 `scope_contract.dimensions` 中每个 `enabled=True` 的维度：

- **核心层（`layer="core"`）** → 走对应的固定 Schema 抽取器：
  1. `core.feature_tree` → 抽取功能列表 → 构建 FeatureTree
  2. `core.pricing_model` → 抽取定价信息 → 构建 PricingModel
  3. `core.user_persona` → 从评论/介绍抽取用户画像 → 构建 UserPersona
  4. `core.swot` → 综合上述三项 + 评论摘要 → 生成 SWOT
- **扩展层（`layer="extension"`）** → 走通用抽取器：
  - 输入：`(dimension.intent, raw_sources_for_this_dimension)`
  - 输出：`ExtensionFinding`（见 §七 7.7），强制带 `source_ids`
  - prompt 中显式注入 `dimension.intent` 作为指向性约束

完成所有维度抽取后，做**多竞品交叉对比** → CrossCompetitorAnalysis（功能矩阵默认只对核心层，扩展层有则附加）

> **跨竞品功能矩阵补全（evidence-gated cross-fill）**：每个竞品的 feature_tree 独立抽取，并集后矩阵稀疏——A 记录的功能对 B/C 默认 `unknown`。补全步骤逐竞品基于**其自身来源**对缺口功能二次分类（supported/partial/unsupported）。**仅当模型引用了确属该竞品的 `source_ids` 时才采纳**，否则保持 `unknown`——严格证据驱动、不依赖世界知识、杜绝幻觉。该步骤永不阻断主流程：任何失败保留原矩阵。仅在真实 LLM 模式生效，CI mock 模式跳过。

**输出语言约定**：所有人类可读文本（功能名、描述、定价档位、用户画像标签/需求/痛点、SWOT 文本、摘要）统一输出为 `WorkflowState.report_language` 所指定的语言（默认 `zh`=简体中文）。产品/品牌名、套餐名、数字和单位保留原文；`source_ids` 逐字复制来源，不翻译。采集仍保留中英双语（权威 dev 工具的官方定价/文档多为英文），语言规范化由 Analyst 的 prompt 指令在抽取时完成。

**输出 Schema**:
- `StructuredCompetitorProfile`（核心层产物，详见 §七 7.4）
- `list[ExtensionFinding]`（扩展层产物，详见 §七 7.7）
- `CrossCompetitorAnalysis`（多竞品对比，详见 §七 7.5）

### Agent 5.3: 撰写 Agent (`WriterAgent`)

**使用模型**：`deepseek-v4-pro`（中文长报告自然度 88，384K 输出容量写完 10-15 页不截断；与 AnalystAgent 同模型简化 prompt 风格协调；详见 §五.X 选型决策）

**职责**: 把结构化 Profile + 扩展产物写成给人看的报告

**渲染规则**：
- 章节顺序、章节标题完全按 `scope_contract.dimensions[].order` 与 `.title` 渲染（**不再硬编码** "5 大板块"）
- 核心章节（`layer="core"`）用对应 Schema 的**固定模板**渲染：
  - feature_tree → 功能矩阵表格
  - pricing_model → 定价对比表 + 文字解读
  - user_persona → 画像卡片
  - swot → SWOT 2×2 网格
  - 保证评委打开任何一份报告都能看到这四种一致的视觉单元
- 扩展章节（`layer="extension"`）用 `ExtensionFinding` 的自由结构渲染：
  - `summary` 必出（段落形式）
  - `bullets` 有则渲染列表
  - `table_data` 有则渲染表格

**输出**:
- 网页结构（JSON，前端渲染用）
- Markdown 全文（用于 PDF/PPTX 导出）
- 每段文字带 `source_ids` 引用，前端渲染时变成可点击的溯源链接
- 多语言报告（P1 答辩前必达）：支持 `language="zh" | "en"`；英文版复用中文报告的 claim/source 结构，只改写语言表达，不允许删除 `source_ids` 或新增无来源结论

**关键约束**: 不允许产生不带引用的结论（强制引用机制，抑制幻觉），核心层和扩展层一视同仁

### Agent 5.4: 质检 Agent (`QAAgent`)

**使用模型**：`gpt-4o-mini`（JSON 结构化检查任务简单，便宜款够用；与跨家协调最少；详见 §五.X 选型决策）

**职责**: 触发反馈闭环

**检查清单（分层判断）**:

| 检查项 | 核心层（`layer="core"`） | 扩展层（`layer="extension"`） |
|---|---|---|
| Schema 完整性 | 必填字段缺失 → **blocker** | 字段稀疏（无 bullets/table_data）→ warning |
| 引用强制 | `source_ids` 缺失 → **blocker** | `source_ids` 缺失 → **blocker**（扩展层也强制溯源） |
| 事实校验 | 抽样 LLM 校验，矛盾 → blocker | 抽样 LLM 校验，矛盾 → warning |
| 数据新鲜度 | 信源 > 2 年 → warning | 信源 > 2 年 → warning |
| 覆盖度 | 每个竞品 ≥ 5 独立信源 → 否则 blocker | 每个维度 ≥ 1 信源 → 否则 warning |

**P1 扩展质量指标（答辩前必达）**：QAAgent 必须对 `report_claims` 写入 `source_support` 与 `validity`，供 `GET /api/reports/{task_id}/metrics` 聚合来源支撑率、无效来源率、信息源类型覆盖率；同时输出 `ai_self_assessment`，报告页与导出摘要页展示"AI 自评 vs 人工验证"对比块。

**SurveyInsight 专项校验**（仅在 `WorkflowState.survey_results` 存在时触发）：

| 检查项 | 级别 | 说明 |
|---|---|---|
| `SurveyInsight.evidence_ids` 非空 | **blocker** | 每条洞察必须关联至少 1 条 `SurveyEvidence`，不可为空列表 |
| 每条 `SurveyInsight` 含 ≥1 条真实来源 | **blocker** | `evidence_ids` 指向的 evidence 中，`source_type` 为 `published_survey` 或 `public_review` 的条数 ≥ 1；不允许一条洞察 100% 由 `ai_simulated` 支撑 |
| `SurveyResult.source_breakdown["ai_simulated"] / total` ≤ 60% | **warning** | 整个 SurveyResult 的模拟占比过高时写入 trace 并在报告页"数据构成"区显示黄色警示；不阻塞流程 |
| `representative_quotes` 含 `ai_simulated` 时前端强制显示 ⚠️ | **约定**（非阻塞） | QAAgent 输出 issue 标记（`severity: "convention"`），前端渲染必须消费此标记；若前端未渲染则视为前端 bug |

**反馈闭环逻辑**：
- **blocker** → 打回 Collector 重抓（最多 3 次），3 次仍失败则字段标"未确认"
- **warning** → 不阻塞流程，在最终报告中标"未充分确认"提示

**实现注记（2026-06-09 补齐）**：
- QAAgent 已补齐核心层 Schema 完整性 blocker：功能矩阵 `unknown` 占比过高、定价 tiers 缺失、用户画像缺失、SWOT 象限过少都会触发打回 Collector。
- Collector 在搜索结果进入抓取前后执行来源相关性闸门，优先保留官网、产品页、应用商店、行业媒体和可信评论，丢弃仅把竞品当作学术样本提及的离题来源，并将 `dropped_irrelevant` 写入采集 errors。
- QA retry 达到上限后，`WorkflowState.field_verification_status` 记录字段级未确认状态，Writer 在报告和指标中以"未确认/公开信息未发现"方式诚实降级，不再把 `unknown` 当作已覆盖字段。

**correction_detected 信号**：QAAgent 输出 blocker 时同步在 `WorkflowState.feedback_signals` 写入 `correction_detected: {target_competitor, failed_field, last_evidence_summary}`，CollectorAgent 重跑时读这个信号，在 prompt 里强调"上次错的是 XX 字段，证据是 YY，这次特别检查 ZZ"，避免无指导性的盲目重抓。借鉴自 DeerFlow memory 模块（见 §五.Y 与 [plans/2026-05-26-deerflow-architecture-inspirations.md](../plans/2026-05-26-deerflow-architecture-inspirations.md) D1）。代码位置：`backend/services/agents/signals.py`。

这套分层保证了 §十三 35% 评分项里"严格符合预定义 Schema、字段完整"对**核心层**始终成立；扩展层走"尽力服务"，缺失也不影响演示主流程。

**输出**:
```json
{
  "passed": "boolean",
  "issues": [
    {
      "severity": "blocker | warning",
      "field": "competitors[0].pricing",
      "reason": "定价字段缺失，未在采集结果中找到",
      "target_agent": "CollectorAgent",  // 打回给谁
      "retry_hint": "请重新搜索 'XXX 定价' 'XXX pricing'"
    }
  ]
}
```

**反馈闭环逻辑**: blocker 级 issue 触发 LangGraph 回到对应节点重跑，最多 3 次。3 次仍失败则标记字段为"未确认"，进入人工介入流程。

### Agent 间通信协议

**约定**: 所有 Agent 间消息通过 LangGraph State 传递，State 是强 Schema 化的 Pydantic Model：

```python
class WorkflowState(BaseModel):
    task_id: str
    user_input: TaskInput
    scope_contract: TaskScopeContract                     # 对话式立项产物
    report_language: str = "zh"                           # 报告目标语言（zh=简体中文）；采集多语，输出规范化
    raw_collections: dict[str, RawCollectionResult]       # competitor → result
    structured_profiles: dict[str, StructuredCompetitorProfile]  # 核心层产物
    extension_findings: list[ExtensionFinding]            # 扩展层产物
    survey_results: dict[str, SurveyResult] | None        # competitor → SurveyResult
    cross_analysis: CrossCompetitorAnalysis | None
    draft_report: ReportDraft | None
    qa_result: QAResult | None
    field_verification_status: dict[str, Any]          # 字段级 verified/unverified/not_applicable 状态
    retry_counts: dict[str, int]                          # node_name → count
    trace_log: list[TraceEntry]                           # 完整决策日志
```

`scope_contract` 在进入 DAG 时已 `frozen`，下游所有 Agent **只读**；保证一次任务的"维度规格"不可在跑批中途漂移。

**SurveyTool trace 命名约定**：SurveyTool 每个 Stage 出口必须写入一条 `TraceEntry`，`stage` 字段命名如下：

| Stage | trace stage 值 |
|---|---|
| Stage 1 问卷设计 | `survey.stage1.designer` |
| Stage 2a 公开调研检索 | `survey.stage2a.existing` |
| Stage 2b 用户声音收集 | `survey.stage2b.voice` |
| Stage 3a 目标画像推断 | `survey.stage3a.persona` |
| Stage 3b 问卷分发 | `survey.stage3b.distribute` |
| Stage 3c 答卷回收 | `survey.stage3c.collect` |
| Stage 4 洞察归纳 | `survey.stage4.aggregate` |

**HybridSearch trace 命名约定**：

| 事件 | trace stage 值 | 必含字段 |
|---|---|---|
| 主搜索调用 | `search.invoke` | `provider`（使用的 provider 名）、`query`、`results_count` |
| Provider 降级 | `search.fallback` | `failed_provider`、`failure_reason`、`next_provider` |
| 全部 provider 失败 | `search.exhausted` | `tried_providers`、`final_error` |

每条 trace entry 需包含：`prompt_hash`、`input_summary`、`output_summary`、`latency_ms`、`tokens_in`、`tokens_out`、`failure_reason`（nullable）、`provider_impl`（Stage 3 Survey 专用，值为 Distributor 实现类名）。

**禁止**：Agent 之间用自然语言对话传消息。所有交互必须通过 State 字段（满足评分项"结构化消息传递 / function calling"）。

**设计辨析：信封 vs 载荷（对标 Claude Code，本系统更严格）**

Claude Code 的父子 Agent 通信也是「异步消息驱动」：父向子的信箱（`pendingMessages`）追加字条、子在 agentic loop 边界自取；子完成后把结果拼成 `<task-notification>` XML **伪装成一条用户消息**注入父对话。这套**传输信封**（异步队列 + 共享状态表 + 完成即通知）的思路值得借鉴，本系统已有对应实现：

| Claude Code 机制 | 本系统对应 |
|---|---|
| `pendingMessages` 信箱 + 子在循环边界自取 | QA blocker → `feedback_signals.correction_detected`，CollectorAgent 重跑时读取（见 5.4） |
| 全局 task 状态表（读写 agent 档案） | `WorkflowState`（强 Schema Pydantic）+ `agent_traces` 表 |
| 异步不阻塞 → 多 subagent 并发 | CollectorAgent `asyncio.gather` 并行采集 5 竞品（见 5.1 并行采集约束） |
| 完成通知注入父对话 | LangGraph 节点进度 SSE 推送（见 §八） |

**但本系统刻意不照搬它的载荷格式**：Claude Code 的 `<result>` / `<summary>` 标签内是**自由文本散文**——父子同为一个通用 LLM，散文够用。本系统的 Agent 间载荷必须是 **Schema 校验过的 Pydantic 对象**（`StructuredCompetitorProfile` / `ExtensionFinding` / `QAResult` …），字段缺失即校验失败、直接触发 QA 打回。

> **一句话**：借其**信封**（异步消息 + 共享状态 + 完成通知），弃其**载荷**（自由文本散文），载荷换成 typed schema。这比 Claude Code 的通信约束更"硬"，正是评分项"结构化消息传递 / function calling，非纯自然语言对话"的硬性兑现，也是答辩时一个清晰的对比叙事点。

---

## 七、竞品知识 Schema 设计

> **架构**：Schema 分**两层**——
> - **核心层（固定）**：7.1 FeatureTree / 7.2 PricingModel / 7.3 UserPersona / 7.4 SWOT。**所有任务都必须产出**，是比赛"严格符合预定义 Schema"评分项的承诺对象。
> - **扩展层（动态）**：7.7 ExtensionFinding。由对话式立项阶段 AI 与用户协商生成（见 §四 [3] 与 7.0 TaskScopeContract），**每个任务的扩展维度不一样**，是"按场景定制"的承诺对象。
>
> QA Agent 对两层做差异化校验：核心层缺失字段 = blocker（硬打回 Collector）；扩展层缺失 = warning（标记"未确认"，不阻塞）。详见 §六 QA Agent 与 §十三 验收标准。

### 7.0 任务范围契约 (`TaskScopeContract`)

对话式立项阶段的最终产出，是 §四 [3] 到 [4] 的交接物，也是后续 4 个 Agent 的"任务规格书"——所有 Agent 决定"做什么 / 抽什么 / 写什么 / 校验什么"都从这里读。

```python
class DimensionSpec(BaseModel):
    id: str                          # "core.feature_tree" / "ext.channel_structure" / "ext.<slug>"
    layer: Literal["core", "extension"]
    source: Literal["system", "ai_suggested", "user_added"]  # 区分来源，决定上限规则
    title: str                       # 用户可改的章节标题：「会员体系与折扣节奏」
    intent: str                      # 用户可改的"意图描述"，喂给 Analyst prompt 做指向性约束
    schema_ref: str | None           # 核心层指向固定 Schema（"FeatureTree" / "PricingModel" 等）；扩展层为 None
    enabled: bool                    # 用户勾选开关（核心层强制 True，UI 上 checkbox 置灰）
    locked: bool                     # 核心层为 True，UI 上禁用删除按钮
    order: int                       # 章节顺序（用户可拖拽调整，核心和扩展可混排）

class UserResearchPlan(BaseModel):
    enabled: bool                    # 用户开关：是否启用用户研究模块（问卷/访谈）
    questionnaire: Questionnaire     # Agent 生成（§7.8），用户可在 scoping 编辑题目；访谈提纲=问卷的一种形态
    prefer_upload: bool              # 用户是否打算上传真实数据（仅 UI 提示；运行时按是否真上传决定数据来源层级）

class TaskScopeContract(BaseModel):
    task_id: str
    target_product: str | None       # 可选——用户描述的"我家产品"
    competitors: list[str]           # 用户确认的竞品名（NL 提取 + chip 合并去重）
    user_brief: str                  # 用户最初的 NL 描述（原文留存，供回溯）
    clarifications: list[dict]       # AI 提的澄清问题 + 用户答案（可为空，用户可全部跳过）
    dimensions: list[DimensionSpec]  # 大纲：核心 4 项 + N 项扩展，按 order 排好
    user_research_plan: UserResearchPlan | None  # 用户研究模块（方案 C 混合）；未启用为 None
    frozen_at: datetime              # 用户点「确认 → 开始分析」的时刻
```

**不变式**：
- `dimensions` 中 `layer="core"` 的条目**恰好 4 项**，对应 7.1-7.4
- 核心 4 项的 `enabled=True`、`locked=True`、`schema_ref` 不可为 None、`source="system"`
- `dimensions` 中 `source="ai_suggested"` 的条目数 **≤ 4**（ScopingAgent 建议上限；`source="user_added"` 不受此约束）
- `source` 字段不变式：`layer="core"` ↔ `source="system"`；`layer="extension"` 时 `source ∈ {"ai_suggested", "user_added"}`
- `frozen` 之后此对象**只读**，进入 LangGraph State 后任何 Agent 不可修改
- 用户点「重新生成大纲」会产生一个**新的**草案对象，旧草案被替换（v1 不做版本回滚，见 §十一 P1）

### 7.1 功能树 (`FeatureTree`)（核心层）

```json
{
  "competitor_id": "string",
  "categories": [
    {
      "name": "核心功能",
      "features": [
        {
          "id": "f1",
          "name": "用户管理",
          "description": "支持邮箱+OAuth登录",
          "support_status": "supported | partial | unsupported | unknown",
          "source_ids": ["src_001", "src_007"]
        }
      ]
    }
  ]
}
```

### 7.2 定价模型 (`PricingModel`)（核心层）

```json
{
  "competitor_id": "string",
  "model_type": "subscription | one_time | freemium | usage_based | enterprise_quote",
  "tiers": [
    {
      "name": "Free / Pro / Enterprise",
      "price": "string",  // 原始字符串保留单位/币种
      "price_normalized_usd_month": "number | null",
      "included_features": ["string"],
      "limits": {"users": 5, "storage_gb": 1},
      "source_ids": ["src_010"]
    }
  ],
  "currency": "USD | CNY | EUR",
  "source_ids": ["string"]
}
```

### 7.3 用户画像 (`UserPersona`)（核心层）

```json
{
  "competitor_id": "string",
  "personas": [
    {
      "label": "中小企业产品经理",
      "size_estimate": "majority | significant | niche",
      "needs": ["string"],
      "pain_points": ["string"],
      "evidence": "string",  // 来自评论/介绍页的原话片段
      "source_ids": ["string"]
    }
  ]
}
```

### 7.4 完整竞品档案 (`StructuredCompetitorProfile`)（核心层聚合）

```json
{
  "competitor_id": "string",
  "name": "string",
  "tagline": "string",
  "official_url": "string",
  "feature_tree": FeatureTree,
  "pricing": PricingModel,
  "user_personas": UserPersona,
  "swot": {
    "strengths": [{"text": "string", "source_ids": [...]}],
    "weaknesses": [...],
    "opportunities": [...],
    "threats": [...]
  },
  "review_summary": {
    "rating_avg": "number | null",
    "review_count": "number | null",
    "top_praise": ["string"],
    "top_complaints": ["string"],
    "source_ids": ["string"]
  }
}
```

### 7.5 跨竞品分析 (`CrossCompetitorAnalysis`)

```json
{
  "feature_matrix": [
    {"feature": "用户管理", "support": {"compA": "yes", "compB": "partial", "compC": "no"}}
  ],
  "pricing_comparison": [...],
  "positioning_map": {
    "x_axis": "price",
    "y_axis": "feature_richness",
    "competitors": [{"id": "compA", "x": 50, "y": 80}]
  },
  "differentiation_summary": "string"
}
```

### 7.6 溯源单元 (`SourceCitation`)

```json
{
  "id": "src_001",
  "type": "url | document | user_uploaded | published_survey | public_review | ai_simulated",
  "category": "official | media | user_feedback | tech_community | commercial | null",  // 信源类型（算信息源类型覆盖率，见 §十三）
  "url": "string",
  "title": "string",
  "snippet": "string",  // 原文片段
  "agent": "CollectorAgent",
  "provider": "string | null",  // 产出该引用的 SearchProvider 实现名（"tavily" / "serpapi" / null）
  "valid": "boolean",  // 来源是否有效（可达 + 相关）；false 计入无效来源率
  "fetched_at": "ISO8601"
}
```

**type 枚举说明**：
- `url` — 普通网页抓取（web_search / fetch_page）
- `document` — 企业 KB 文档上传（本期不实现，枚举占位，见 §十一-bis / §十一-ter）
- `user_uploaded` — 用户上传的真实问卷结果 / 访谈记录（方案 C，对应 `SurveyEvidence.user_uploaded_primary`；上传即脱敏）
- `published_survey` — 公开调研报告 / 行业数字（SurveyTool Stage 2a）
- `public_review` — 公开评论 / 社媒帖子（SurveyTool Stage 2b）
- `ai_simulated` — LLM 模拟答卷（SurveyTool Stage 3，**必须显示 ⚠️ AI 生成标记**）
- ~~`simulated_survey`~~ → 废弃，统一用 `ai_simulated`（如有历史数据迁移到 `ai_simulated`）

**`category` 枚举说明**（与 `type` 正交，用于"信息源类型覆盖率"，见 §十三 业务价值指标）：
- `official` — 官网 / 产品文档 / 定价页 / 官方博客
- `media` — 新闻 / 第三方测评文章
- `user_feedback` — 评论 / 社媒（Reddit / 知乎 / App Store / Product Hunt）
- `tech_community` — GitHub / 开发者论坛 / Stack Overflow
- `commercial` — 融资 / 招聘 / 企业客户案例
- 目标信源类型数默认 5（即上述全部）；`信息源类型覆盖率 = 命中的 category 数 / 5`

所有报告字段中的 `source_ids: ["src_001", ...]` 都指向 `SourceCitation`，前端渲染时变成可点击图标。`ai_simulated` 类型在前端渲染时**强制**显示灰色 badge + 🤖 图标 + ⚠️ 警示标，不可省略。

### 7.7 扩展维度产出 (`ExtensionFinding`)（扩展层）

承接对话式立项阶段动态生成的扩展维度。每个扩展维度 × 每个竞品产出一条 `ExtensionFinding`。

```python
class ExtensionFinding(BaseModel):
    dimension_id: str                # 对应 TaskScopeContract.dimensions[].id，必为 "ext.*"
    competitor_id: str
    summary: str                     # 1-2 段自然语言总结
    bullets: list[str] | None        # 可选要点列表（结构化呈现给报告）
    table_data: list[dict] | None    # 可选结构化对比数据（如价格区间表）
    source_ids: list[str]            # 强制引用：至少 1 条，与 7.6 SourceCitation 关联
```

**强制约束**：
- `source_ids` **不可为空**——比赛 35% 评分项明文要求"每条结论可定位到原始数据源"，扩展层与核心层享受同等溯源待遇
- `summary` 不可为空，是 Writer Agent 渲染章节的最低产物
- `bullets` / `table_data` 由 Analyst Agent 按维度 `intent` 自决定要不要填，QA 不强制

**与核心层的差别**（决定 QA 行为）：
- 核心层 Schema 字段缺失 → QA 标 blocker → 打回 Collector 重抓（触发反馈闭环）
- 扩展层 `ExtensionFinding` 缺失或字段稀疏 → QA 标 warning → 报告里那一节标"未充分确认" → 不阻塞流程

---

### 7.8 Survey 系列 Schema

> SurveyTool 产物的完整 Pydantic Schema 定义。存放于 `backend/schemas/survey.py`。
> 所有 `SurveyEvidence.source_id` 指向 §7.6 `SourceCitation`，不破坏现有溯源模型。

```python
# backend/schemas/survey.py

from datetime import datetime
from typing import Literal
from pydantic import BaseModel

# ─── 问卷设计层 ────────────────────────────────────────────────

class SurveyQuestion(BaseModel):
    id: str                                        # "sq_001"
    text: str                                      # 题目原文
    type: Literal["open", "multiple_choice", "scale"]
    options: list[str] | None                      # 选择题 / 量表题选项
    intent: str                                    # 这道题想了解什么

class Questionnaire(BaseModel):
    id: str                                        # "qn_<uuid>"，供 DistributionHandle 引用
    competitor: str
    dimension_intent: str                          # 来自 TaskScopeContract.dimensions[].intent
    questions: list[SurveyQuestion]                # 5-10 道
    design_rationale: str                          # AI 解释为什么这样设计

# ─── 目标画像层 ────────────────────────────────────────────────

class TargetPersona(BaseModel):
    label: str                                     # "高消费会员"
    traits: str                                    # "年消费 5 万+，会员等级 V5+"
    est_size: Literal["majority", "significant", "niche"]
    inferred_from: list[str]                       # source_ids（推断画像所依据的源）

# ─── 分发回收层 ────────────────────────────────────────────────

class DistributionHandle(BaseModel):
    id: str                                        # "dist_<uuid>"
    distributor_impl: str                          # "SimulatedDistributor" / "TypeformDistributor"
    questionnaire_id: str                          # 指向 Questionnaire.id
    target_personas: list[TargetPersona]
    sample_size: int
    status: Literal["dispatched", "collecting", "completed", "failed"]
    dispatched_at: datetime

class SurveyResponse(BaseModel):
    id: str
    distribution_id: str
    persona: TargetPersona
    answers: dict[str, str]                        # question_id → 答案文本
    submitted_at: datetime

# ─── Evidence + Insight 层（报告渲染用）──────────────────────

class SurveyEvidence(BaseModel):
    id: str
    question_id: str                               # 关联到具体题目
    source_type: Literal[
        "user_uploaded_primary",                   # 一手：用户上传的真实问卷结果 / 访谈记录（最高可信，方案 C）
        "published_survey",                        # Stage 2a：公开调研报告 / 行业数字
        "public_review",                           # Stage 2b：公开评论 / 社媒
        "ai_simulated",                            # Stage 3：LLM 模拟答卷（⚠️ 必须标注，仅无上传时兜底）
    ]
    source_id: str                                 # 指向 §7.6 SourceCitation
    raw_quote: str                                 # 原文片段 / 模拟回答文本（上传数据已脱敏）
    persona_inferred: str | None                   # LLM 推断的画像标签

class SurveyInsight(BaseModel):
    question_id: str
    point: str                                     # "黑卡门槛过高"
    frequency: int                                 # 在 evidence 里出现次数
    representative_quotes: list[str]               # 代表性原话 2-3 句
    evidence_ids: list[str]                        # 强制溯源，非空（QAAgent blocker）
    confidence: Literal["high", "medium", "low"]  # 按 source_type 构成自动推断

# confidence 推断规则：
#   real_ratio = (user_uploaded_primary + published_survey + public_review 数) / total evidence 数
#   （user_uploaded_primary 计入真实来源，权重最高）
#   real_ratio >= 0.7 → "high"；>= 0.3 → "medium"；else → "low"

# ─── 顶层产物 ──────────────────────────────────────────────────

class SurveyResult(BaseModel):
    competitor: str
    dimension_intent: str
    questionnaire: Questionnaire
    target_personas: list[TargetPersona]
    distribution: DistributionHandle
    responses: list[SurveyResponse]                # Distributor 原始答卷
    evidence: list[SurveyEvidence]                 # 3 种 source_type 混合
    insights: list[SurveyInsight]
    coverage_note: str
    source_breakdown: dict[str, int]               # {"published_survey": 8, "public_review": 12, "ai_simulated": 12}
```

**强制约束**：
- `SurveyInsight.evidence_ids` 不可为空（§六 5.4 QAAgent blocker）
- 每条 `SurveyInsight` 至少 1 条真实来源（`published_survey` 或 `public_review`）
- `ai_simulated` 证据在报告页必须显示 ⚠️ AI 生成标记，前端渲染不可省略
- `SurveyResult` 存入 `WorkflowState.survey_results[competitor]`

### 7.9 Claim 注册表 (`ReportClaim`) — 质量指标的统一计量单元

> 业务闭环量化指标（§十三）的事实源。**核心抽象：一个 claim = 报告中任何带 `source_ids`（或 Survey 的 `evidence_ids`）的 Schema 节点**——因为 PRD 本就强制每条结论挂源，所以"claim 清单"天然已存在，只需在报告 finalize 时由 **claim extractor** 遍历 Report JSON 抽出落库。所有指标都是对这份清单的聚合，口径自洽。

**claim extractor 规则**（哪些节点 = 1 条 claim）：
- 核心层：每个 feature（7.1）/ 每个 pricing tier + model_type（7.2）/ 每个 persona（7.3）/ 每条 SWOT 条目（7.4）/ review_summary（7.4）
- 跨竞品：feature_matrix 每行 / differentiation_summary（7.5）
- 扩展层：每条 `ExtensionFinding`（7.7）
- Survey：每条 `SurveyInsight`（7.8，用 `evidence_ids` 代 `source_ids`）

```python
class ReportClaim(BaseModel):
    id: str                          # "clm_<uuid>"
    report_id: str
    claim_path: str                  # JSON 路径，如 "compA.pricing.tiers[1].price"
    claim_text: str                  # v1 渲染文本快照（用于人工修正 diff）
    layer: Literal["core", "extension", "survey"]
    field_type: Literal["structured", "free_text"]  # structured=价格/状态/枚举；决定修正是否算"事实修正"
    source_ids: list[str]            # 关联 §7.6 SourceCitation（Survey 用 evidence_ids 映射）
    generating_agent: str            # Collector / Analyst / Writer
    qa_status: Literal["pass", "warning", "blocker"]
    source_support: Literal["supported", "weak", "unsupported", "unchecked"]  # QA 判定来源是否支撑该结论
    edit_status: Literal["untouched", "edited"]      # 关联 manual_corrections
    review_status: Literal["unreviewed", "correct", "partial", "wrong", "unverifiable"]  # 人工复核
```

**不变式 / 约束**：
- `T = 报告 claim 总数`，是所有"率"型指标的分母，报告 finalize 后冻结
- `引用覆盖率 = source_ids 非空的 claim / T`（直接等价于现有强制溯源要求）
- claim 的三态（`source_ids` 有无 / `source_support` / `review_status`）支撑"引用覆盖率 ⊇ 来源支撑率 ⊇ 人工确认准确率"三层递进叙事
- 计算公式与展示见 §十三 业务价值指标

---

## 八、API 划分

### 8.1 认证
- `POST /api/auth/login` — demo 一键登录（传入内置邮箱直接签发 JWT 并落 httpOnly cookie，无验证码）
- `GET /api/auth/me` — 当前用户信息

### 8.2 任务
- `POST /api/tasks` — 创建任务（含目标产品、竞品列表、维度选择）
- `GET /api/tasks` — 列表（我的任务）
- `GET /api/tasks/{id}` — 任务详情（含报告）
- `DELETE /api/tasks/{id}` — 删除

### 8.3 任务执行与可观测
- `POST /api/tasks/{id}/run` — 启动 Agent DAG（异步，返回 run_id）
- `GET /api/tasks/{id}/stream` — **SSE 推送**：实时 DAG 状态、Agent 当前步骤、Trace 增量
- `GET /api/tasks/{id}/trace` — 完整执行日志（每个 Agent 的 prompt / input / output / token / 时间）
- `GET /api/tasks/{run_id}/timeline` — Agent 决策时间轴回放（按 `agent_traces.sequence_no/created_at` 排序，返回节点开始/结束、关键输入摘要、决策摘要、QA 打回原因、重跑链路）
- `POST /api/tasks/{id}/retry-node` — 用户手动触发某节点重跑

### 8.4 报告
- `GET /api/reports/{task_id}` — 网页渲染数据（结构化 JSON）
- `GET /api/reports/{task_id}/export?format=pdf|pptx|markdown` — 导出（含质量指标摘要页）
- `PATCH /api/reports/{task_id}/field` — 人工修正某字段（body 带 `correction_type`：事实修正/表述优化/补充信息/删除无效/结构调整；写 `manual_corrections` + 更新对应 `ReportClaim.edit_status`，可触发局部重跑）
- `PATCH /api/reports/{task_id}/claims/{claim_id}/review` — 人工复核某 claim（body：`review_status` ∈ correct/partial/wrong/unverifiable），产出人工确认准确率
- `POST /api/reports/{task_id}/dimensions/{dimension_id}/regenerate` — 用户要求某模块重新生成（复用反馈闭环路由，计重跑率）
- `GET /api/reports/{task_id}/metrics` — 聚合返回 P0 MVP-5 + P1 扩展质量指标（§十三），生成时指标 + 人工闭环指标
- `GET /api/reports/search?q=...` — 历史报告语义检索（pgvector），返回可复用的历史 report / claim / source 片段；仅检索本用户历史报告，不接企业 KB
- `POST /api/reports/{task_id}/language` — 生成或切换报告语言（body：`language` ∈ `zh`/`en`），所有语言版本必须保留同一套 `source_ids`

### 8.5 竞品推荐（B 入口）
- `POST /api/competitors/suggest` — 输入产品+赛道描述，返回竞品候选

### 8.6 用户研究模块（方案 C）
- `POST /api/tasks/{id}/survey/upload` — 上传真实问卷结果（CSV）/ 访谈记录（文本）→ **上传即脱敏**（去姓名/手机/邮箱）→ 解析为 `SurveyEvidence(source_type="user_uploaded_primary")` → 写 `survey_uploads` 表
  - 边界：仅接问卷结果 / 访谈记录，**不是**通用文档 / 企业 KB 上传（后者仍 P2，见 §十一-bis）

---

## 九、前端线框图（文字描述）

### 页面 1a: 任务创建页 `/tasks/new`
```
┌─────────────────────────────────────────────────────────┐
│ [Logo] AI 竞品分析                                 [我] │
├─────────────────────────────────────────────────────────┤
│ Strata AI                                               │
│ 多 Agent 竞品情报平台                                    │
│                                                         │
│ 描述你的竞品分析需求。默认情况下，Strata 会先生成研究    │
│ 大纲供你确认；如果需求已经足够明确，或你明确要求"直接    │
│ 生成"，Strata 将跳过大纲直接开始分析。                  │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 例：对比 Trae、Cursor、GitHub Copilot 在 AI 编程  │ │
│ │ 辅助上的差异，重点关注开发者体验与企业版定价…    │ │
│ │                                              42 字 │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 示例快填： (Trae · AI 编程) (飞书 · 企业协作) (抖音…)   │
│                                                         │
│                              [生成研究计划 →]           │
└─────────────────────────────────────────────────────────┘
```
> **页面约束**：只有 NL 单输入 + 示例 chips + 主操作按钮。竞品名 chip 输入区不存在（已知竞品由 ScopingAgent 从 NL 提取，立项页才允许增删）。「30 秒演示」入口在全站顶部导航栏。
>
> **按钮文案双态**：当 NL 含「直接生成 / 跳过 / 不要大纲 / directly / skip / no plan」等关键词时，按钮文案切换为「直接分析 →」，提交后跳过 scoping 页直接进入分析（演示路径 `/demo/scoping`）。否则默认「生成研究计划」走 ScopingAgent。

### 页面 1b: 对话式立项 / scoping 页 `/tasks/new/scoping`
```
┌─────────────────────────────────────────────────────────┐
│ 识别到的竞品：[SK-II ×] [资生堂 ×] [雅诗兰黛 ×] [+]    │
│                                                         │
│ 本次分析维度（拖动调整顺序）                             │
│                                                         │
│  ☑ 🔒 功能树                                  ⇅       │
│     "对比三家核心产品线与功能矩阵"  [✎]                  │
│                                                         │
│  ☑ 🔒 定价模型                                ⇅       │
│     "重点看会员体系与折扣节奏"  [✎]                      │
│                                                         │
│  ☑ 🔒 用户画像                                ⇅       │
│     "..."  [✎]                                          │
│                                                         │
│  ☑ 🔒 SWOT                                    ⇅       │
│                                                         │
│  ☑ ✏️ 会员体系与折扣节奏                       ⇅  [×] │
│     "电商旗舰店黑卡 / 积分 / 大促节奏"  [✎]              │
│                                                         │
│  ☑ ✏️ KOL 与代言矩阵                           ⇅  [×] │
│     "代言人 + 头部主播合作"  [✎]                         │
│                                                         │
│  ☐ ✏️ 历史价格变化                             ⇅  [×] │
│     "近 1 年价格趋势 + 大促涨跌"  [✎]                    │
│                                                         │
│  [ + 增加自定义维度 ]                                   │
│                                                         │
│ ▾ 用户研究计划（方案 C，可折叠卡片）      [启用 ●—○]    │
│   问卷/访谈提纲（AI 生成，可编辑）：                     │
│    1. 你最看重会员体系的哪一点？        [✎]            │
│    2. ...（5-10 题，可增删改）          [✎]            │
│   数据来源：① 上传真实问卷结果/访谈记录 [⬆ 上传]        │
│            ② 无上传 → 公开调研+评论 ③ 模拟样本兜底⚠️    │
│                                                         │
│ ─────────────────────────────────────────────           │
│ 为了更准，AI 想确认（可跳过）：                          │
│   ▢ 报告主要给谁看？  ( ) PM ( ) 高管 ( ) 客户          │
│   ▢ 需要历史变化对比吗？  ( ) 是 ( ) 否                  │
│                                                         │
│             [重新生成大纲]   [确认 → 开始分析]          │
└─────────────────────────────────────────────────────────┘
```

**交互细节**：
- 🔒 标记 = 核心层（`layer="core"`、`source="system"`），删除按钮置灰；[✎] 改名和意图始终开启
- ✏️ 标记 = 扩展层（`layer="extension"`），所有按钮可用
- 扩展维度区顶部显示「**AI 建议 (n/4)**」计数器（按 `source="ai_suggested"` 实时统计）；到 4 时「重新生成大纲」按钮 tooltip 提示已达 AI 建议上限，但用户仍可通过下方「+ 自定义维度」无限手加（`source="user_added"`，不计入 n/4）
- 拖动手柄 ⇅ 调整 `dimensions[].order`，核心和扩展可混排
- **可折叠卡片**：分析维度 / 用户研究计划 等长模块做成可展开/收起卡片（展开编辑、收起更简洁，页面更美观）；前端实现走 `frontend-design` + `web-design-guidelines` skill
- **用户研究计划卡片**（方案 C）：启用开关（关 → 整个用户研究模块跳过）；问卷题目 AI 生成 + 用户可增删改；「⬆ 上传」可传真实问卷结果（CSV）/ 访谈记录（文本）→ 一手数据（上传即脱敏，§八 8.6）；不上传则运行时退化为 公开二手 + 模拟兜底
- 「重新生成大纲」= 带当前编辑过的章节 + 澄清回答回到 AI 再生成一版（不是完全推倒）。AI 输出最多 4 个 `ai_suggested`，已有 `user_added` 条目保留
- 「确认 → 开始分析」时把当前状态 freeze 成 TaskScopeContract（见 §七 7.0），后续不可改

### 页面 2: 任务进行中 `/tasks/{id}`（实时 DAG）
```
┌─────────────────────────────────────────┐
│  左侧 (40%)            │  右侧 (60%)    │
│  DAG 可视化            │  Trace 详情    │
│                        │                │
│  [采集Agent]●在跑       │  时间  Agent  事件
│   ├─ Tavily搜索...     │  10:01 Collector start
│   └─ 已采集 12 源      │  10:02 search "X定价"
│  [分析Agent]○等待       │  10:02 found 8 URLs
│  [撰写Agent]○等待       │  ...
│  [质检Agent]○等待       │  [点击展开任意行→看
│                        │   prompt/input/output]
│  进度: 35%  预计 3min  │                │
└─────────────────────────────────────────┘
```

### 页面 3: 报告查看 `/reports/{id}`
```
┌──────────────────────────────────────────┬──── 质量面板 ────┐
│  [产品A vs 产品B vs 产品C]                │ 分析耗时 7m12s   │
│  [导出PDF] [导出PPTX] [回放DAG] [复核模式]│ 检索源 64 / 有效 28│
│  徽章带: 字段覆盖 91% · 引用覆盖 88% · 信源28│ 字段覆盖率 91%   │
├──────────────────────────────────────────┤ 需求覆盖率 100%  │
│ § 摘要                                    │ 引用覆盖率 88%   │
│ 三款产品在...有显著差异 [src①②]          │ 来源支撑率 82%   │
│                                          │ 人工修正率 14%   │
│ § 功能对比矩阵                            │ 人工确认准确率 89%│
│ │ 用户管理│ ✓ │ △ [src][✎] │ ✗ │        │ 待复核 7 条      │
│   ↑每个 claim 可行内编辑[✎]/复核标记      ├──────────────────┤
│ § SWOT / 定价对比 / 用户画像              │ AI自评→人工验证   │
│ § 用户声音洞察（Survey）⚠️                │ 引用88→支撑82→准确89│
│                                          │ 修正类型堆叠条     │
│ claim 视觉态: 未触碰/已修正(diff)/已确认  │                  │
│ [点击 src → 溯源面板] [改某 claim→记修正] └──────────────────┘
└──────────────────────────────────────────┘
```
**质量面板说明**（§十三 业务价值指标的产品载体）：
- 头部徽章带（生成时即显示，自动指标）：字段覆盖率 / 引用覆盖率 / 信源数 / 分析耗时
- 右侧质量面板：全部指标（仿运营 dashboard），含人工闭环指标（随编辑/复核实时更新）
- **每个 claim 行内可编辑 [✎]**（PATCH /field，选 `correction_type`）+ 可复核标记（复核模式下标 正确/部分/错误/无法判断）
- claim 视觉态：未触碰 / 已人工修正（diff 高亮 old→new）/ 已确认 / 待复核 / ⚠️ai_simulated
- "AI 自评 vs 人工验证"对比块：引用覆盖率 → 来源支撑率 → 人工确认准确率 三层递进 + 修正类型堆叠

### 页面 4: 溯源面板（侧滑）
```
点击 [src②] →
┌─────────────────────────────────────────┐
│ × 来源详情                              │
│ 类型: 官网                              │
│ URL: https://example.com/pricing        │
│ 抓取时间: 2026-05-21 10:03              │
│ 由 CollectorAgent 采集                  │
│ ─────────────────                       │
│ 原文片段:                               │
│ "Our Pro plan starts at $29/month..."   │
│ [访问原网页 ↗]                          │
└─────────────────────────────────────────┘
```

### 页面 5: 我的报告 `/tasks`
表格列表：任务名、创建时间、状态、操作（查看/重跑/删除）

---

## 十、数据库 Schema (Neon Postgres)

```sql
-- 用户
users (id uuid PK, email text UNIQUE, created_at, last_login_at)

-- 任务
tasks (
  id uuid PK, user_id FK,
  target_product text, target_brief text,
  competitor_names jsonb,                  -- 用户输入的竞品名列表
  dimensions jsonb,                         -- 启用的分析维度
  status text,                              -- pending/running/completed/failed
  created_at, started_at, completed_at
)

-- 任务运行实例（一次任务可能重跑多次）
task_runs (
  id uuid PK,                              -- run_id（SSE/StreamBridge 的订阅 key）
  task_id FK,
  status text,                              -- pending/running/succeeded/failed/cancelled
  retry_count int,
  langgraph_thread_id text,                -- LangGraph PostgresCheckpointer 的 thread_id（与本表 id 一一对应）
  checkpoint_id text,                       -- 最后一次成功 checkpoint，支持失败续跑
  error_summary jsonb,                      -- 失败时记录 {stage, agent, exception_class, message, blocker_after_3_retries}
  started_at, completed_at,
  cancelled_at                              -- 用户主动取消时间戳（区别于 failed）
)

-- Trace 日志（每个 Agent 节点一条）
agent_traces (
  id uuid PK, task_run_id FK,
  sequence_no int,                         -- 单个 run 内严格递增，用于时间轴回放
  agent_name text, node_name text,
  status text,                             -- started/succeeded/failed/skipped/retried
  prompt text, input_payload jsonb, output_payload jsonb,
  tokens_in int, tokens_out int,           -- 与 §五.Y 约束 3 一致
  cost_usd numeric,                         -- 按 §五.X 模型单价 × token 估算
  latency_ms int,
  langsmith_run_id text,                    -- 关联 LangSmith trace（§五.Y 约束 6，可空）
  decision_meta jsonb,                     -- 决策摘要（为何打回等）
  started_at, completed_at, created_at
)

-- 信源
source_citations (
  id text PK,                              -- src_001 etc
  task_id FK,
  type text, url text, title text, snippet text,
  raw_content text,
  embedding vector(1536),                  -- pgvector，用于复用检索
  fetched_at, fetched_by_agent text
)

-- 竞品档案（结构化产出）
competitor_profiles (
  id uuid PK, task_id FK, competitor_name text,
  feature_tree jsonb, pricing jsonb, user_personas jsonb,
  swot jsonb, review_summary jsonb,
  updated_at
)

-- 跨竞品分析
cross_analyses (
  id uuid PK, task_id FK,
  feature_matrix jsonb, pricing_comparison jsonb,
  positioning_map jsonb, differentiation_summary text,
  updated_at
)

-- 报告（撰写 Agent 产物）
reports (
  id uuid PK, task_id FK,
  structured_content jsonb,                -- 前端渲染用
  markdown_content text,                   -- 导出用
  language text,                            -- zh/en；默认 zh
  source_report_id uuid nullable,           -- 英文版等派生报告指回原报告
  version int,
  qa_status text,                          -- passed/issues
  qa_issues jsonb,
  metrics jsonb,                           -- 业务价值指标快照（§十三）：生成时指标 + 人工闭环指标聚合
  embedding vector(1536),                  -- 历史报告语义检索，S5/P1 必达
  created_at
)

-- Claim 注册表（质量指标统一计量单元，§7.9；报告 finalize 时由 claim extractor 落库）
report_claims (
  id uuid PK, report_id FK,
  claim_path text, claim_text text,        -- JSON 路径 + v1 文本快照（diff 用）
  layer text,                              -- core/extension/survey
  field_type text,                         -- structured/free_text
  source_ids jsonb,
  generating_agent text,
  qa_status text,                          -- pass/warning/blocker
  source_support text,                     -- supported/weak/unsupported/unchecked
  validity text,                            -- valid/invalid/stale/unknown，用于无效来源率
  edit_status text,                        -- untouched/edited
  review_status text,                      -- unreviewed/correct/partial/wrong/unverifiable
  correction_type text,                     -- null 或 5 类修正类型，便于 P1 细分
  embedding vector(1536),                  -- claim 级历史复用检索
  created_at
)

-- 人工修正历史（P0，业务闭环；原 P1 提级）
manual_corrections (
  id uuid PK, report_id FK, claim_id FK,   -- 关联 report_claims
  field_path text, old_value jsonb, new_value jsonb,
  correction_type text,                    -- 事实修正/表述优化/补充信息/删除无效/结构调整
  triggered_rerun boolean, user_id FK, created_at
)

-- 用户研究一手数据上传（方案 C，§八 8.6）
survey_uploads (
  id uuid PK, task_id FK,
  kind text,                               -- questionnaire_result（CSV）/ interview_record（文本）
  filename text, original_size int,
  redacted_content jsonb,                  -- 解析 + 脱敏后内容（去姓名/手机/邮箱）；原始文件不长期留存
  parsed_evidence_count int,               -- 解析出的 SurveyEvidence 条数（source_type=user_uploaded_primary）
  uploaded_by FK, created_at
)
```

---

## 十一、功能清单与优先级

### P0 (MVP，第一期必须，3 周内交付)

| 模块 | 功能 | 验收要点 |
|---|---|---|
| Auth | 邮箱验证码登录 | 5 分钟内可注册并发起首次任务 |
| 任务 | 手动输入竞品 / AI 推荐竞品并确认 | 两种入口都可用 |
| Agent | 4 Agent + LangGraph 编排 | DAG 节点齐全 |
| Agent | 反馈闭环（QA 打回重做）| 必须能现场触发：故意构造缺失数据 → QA 打回 → 重跑后改善 |
| 可观测 | DAG 实时可视化 + Trace 日志 | 每个节点的 prompt/input/output/token 可查 |
| Schema | 功能树+定价+画像+SWOT 全部按 Schema 输出 | 字段完整率 100% |
| 溯源 | 每条结论可点击溯源 | 一键定位到原始 URL+片段 |
| 报告 | 网页交互式报告 | 5 大板块齐全（摘要/功能矩阵/SWOT/定价/画像）|
| 导出 | PDF 导出 | 字段不丢失，含引用 |
| 导出 | PPTX 导出（汇报用）| 自动生成 10-15 页结构化 PPT |
| 部署 | Railway 公网可访问 | 评委用链接即可试用 |
| 业务闭环 | 人工介入修正字段（行内编辑 + correction_type）+ 触发局部重跑 | 修改即写 `manual_corrections`，可现场演示 |
| 业务闭环 | 质量指标面板（MVP-5：分析耗时/字段覆盖率/引用覆盖率/人工修正率/人工确认准确率）| claim 级聚合，报告页可见 + 导出摘要页（详见 §十三） |
| 用户研究 | 用户研究模块（方案 C）：AI 生成问卷/访谈提纲 + 用户可编辑 + 启用开关 | scoping 折叠卡片，可开关 |
| 用户研究 | 数据来源三层：上传真实问卷/访谈记录（一手）> 公开二手 > 模拟兜底 | 上传即脱敏；source_type 区分可信度 |

### P1 (答辩前增强必达项)

> P1 不再是"时间允许再做"的加分范围，而是**答辩前必须完成**的增强能力；区别只在交付顺序：P0 先保证主链路稳定可演示，P1 在 S5 前补齐产品完整度和评分增强项。

- 扩展质量指标：来源支撑率（QA 判源）、信息源类型覆盖率、无效来源率、重跑率、修正类型 5 分类细分、AI 自评vs人工验证对比块；报告页和导出摘要页都可见
- Agent 决策时间轴回放：`GET /api/tasks/{run_id}/timeline` + 前端 Trace/Timeline 面板可查看每个节点的输入摘要、输出摘要、失败原因、QA 打回和重跑链路
- 历史报告语义检索（RAG 复用素材）：`GET /api/reports/search?q=...` 基于本用户历史 `reports/report_claims` 的 pgvector 检索；不接企业 KB，不上传公司内部资料
- 应用商店评论真实抓取：CollectorAgent 增加 app review provider；失败时降级到公开网页/模拟兜底，并在 `SourceCitation.type/source_type` 明确标识真实来源或 `ai_simulated`
- 多语言报告（中/英切换）：WriterAgent 支持 `zh/en` 输出模板；英文版必须复用原报告 claim/source 结构，不能丢 `source_ids`

### P2 (远期，PRD 仅占位；本轮比赛不做)

- 全自动竞品发现（仅赛道关键词输入）
- 自适应任务拆分（Agent 自决定要不要拆子任务）
- Agent 自评估 + 动态 Schema 演化
- 多人协作编辑同一报告

---

## 十一-bis、Non-Goals（本次比赛 MVP 显式不做的事）

> 把"不做的事"写死比把"要做的事"写全更重要——避免开发 Agent 在 3 周窗口里
> 自己脑补加企业级特性，挤压 Agent 核心功能的时间。

### 账号与权限层面
- ❌ OAuth 第三方登录（GitHub / Google / 微信）—— 邮箱验证码够评委用
- ❌ 密码登录 / 找回密码 / 邮箱变更等账号管理流程
- ❌ 团队空间 / 多租户 / 组织架构
- ❌ RBAC / 字段级权限 / 报告分享链接的权限分级

### 并发与扩展性层面
- ❌ 水平扩容 / 多实例部署 / 负载均衡
- ❌ Web 层限流（rate limiting middleware）/ WAF
- ❌ Redis 分布式锁 / 分布式事务
- ❌ SLO / SLA 定义与监控告警体系
- ❌ 真实用户并发压测（演示日靠 Railway 临时升档 + 预置账号兜底，见 §十二 风险表）

### 数据与合规层面（MVP 外）
- ❌ GDPR / 数据出域审计 / 完整数据脱敏管线（但方案 C 上传问卷/访谈记录时做**最小脱敏**：去姓名/手机/邮箱，§八 8.6——这是合规底线，不是完整管线）
- ❌ 内部数据上传（如 §十四 G 提到的"上传公司销售数据" / 企业 KB 文档）—— 留给 P2
  - ℹ️ **边界澄清**：方案 C 的"上传**问卷结果 / 访谈记录**"（§八 8.6）**属于 P0 in scope**，与此处的"企业 KB / 销售数据上传"不同——前者是用户研究模块的一手数据（窄范围 + 强制脱敏），后者是通用异构知识库（仍 P2）
- ❌ 企业 KB / 通用外部文档 RAG（Confluence、SharePoint、付费数据库、内部销售数据等仍为 P2）—— 本轮 P1 只做**历史报告语义检索**，数据来源限定为本系统已经生成并可溯源的 `reports/report_claims/source_citations`
- ℹ️ 国内合规 LLM —— MVP 已部分国产化（AnalystAgent + WriterAgent 用 DeepSeek V4 Pro，见 §五.X）；生产化阶段补充更多国产 Provider，见 §十一-ter 第二阶段

### 仍然要做的（提醒）
- ✅ **单任务内多 Agent 并行**（LangGraph `Send` API 做 fan-out，4 个竞品的采集并行而非串行）
  —— 这不是"高并发"，是单任务内的并行度优化，**直接影响演示节奏**
- ✅ **演示日运维预案**：Railway 临时升档 + 预置 3 个评委账号 + 完整的**演示模式（Demo Mode）静态回放路径**（详见 §十一-quater）

---

## 十一-ter、未来生产化路径（答辩用 / 路演用）

> 本节不是 MVP 要做的事，是回答"这个 Agent 系统能不能从演示走到真实生产"。
> 答辩被问到"商业化路径 / 扩展性"时可直接引用本节。

### 第一阶段：从演示到内测（约 +2-4 周工程量）
触发条件：找到 1-2 个真实付费意向的客户（如汉高战略部内部使用）。

| 模块 | 升级动作 | 工程量 |
|---|---|---|
| 账号 | 邮箱验证码 → OAuth（GitHub/Google）+ 简单团队空间 | ~1 周 |
| 部署 | Railway Hobby → Railway Pro / 自建 VPS（2 vCPU + 4G） | ~2 天 |
| 数据库 | Neon Free 3GB → Neon Pro（无容量焦虑）+ pgvector 索引调优 | ~2 天 |
| 限流 | 加 FastAPI middleware 做按用户的 RPS 限流 + LLM token 配额 | ~3 天 |
| 监控 | Sentry 错误监控 + 简易 Grafana（Agent 延迟 / 成功率 / 成本） | ~3 天 |

### 第二阶段：从内测到生产（约 +1-2 月工程量）
触发条件：DAU 上百，单日任务量 ≥ 500。

| 瓶颈 | 解法 | 备注 |
|---|---|---|
| **LLM API 速率** | 多 key 池 + 智能路由（GPT-4o → GPT-4.1-mini fallback） | 这是真正的瓶颈，不是 web 层 |
| **采集 API 速率** | Tavily 免费 → 付费；Playwright 抓取走代理池 | 合规边界在这一步显化 |
| **任务队列** | Upstash Redis → 自建 Redis Cluster / 用 Celery + Redis Broker | 当前 LangGraph checkpointer 已支持 |
| **多实例** | FastAPI 单实例 → K8s/Fly.io 多实例 + sticky session（SSE 长连接） | SSE 是最麻烦的，要么换 WebSocket 要么粘性 |
| **数据库** | Neon → 自建 PG / 云厂商托管 + 主从读写分离 | 主要瓶颈在 pgvector 相似度检索 |
| **合规** | MVP 已用 DeepSeek V4 Pro（Analyst+Writer）部分国产化；生产化补充智谱 GLM / 阿里通义 / MiniMax 多 Provider + 国内云直连 | 客户在国内必走；详见 §五.X |

### 第三阶段：真正的 SaaS 化（远期，不在 12 个月规划内）
- 多租户隔离（数据库 schema-per-tenant 或 row-level security）
- 按用量计费 / 订阅计费集成（Stripe / 国内支付）
- 报告分享链接的权限分级 / 水印 / 过期机制
- 自动竞品发现（§十一 P2 提到的）作为差异化卖点

### 设计上为未来留的钩子（**这一段是答辩重点**）
当前 MVP 在以下几处已经"为未来做了准备"，体现架构前瞻性：

1. **Pydantic State + LangGraph checkpointer** —— 任意时刻可序列化中断/恢复，
   未来切到分布式队列只是换 backend，业务逻辑不动
2. **pgvector 已接入** —— 未来做"历史报告语义检索复用"只是上层 query 改造
3. **TaskScopeContract** —— Agent 的"做什么"与"怎么做"已解耦，
   未来加新行业模板不用改 Agent 代码
4. **所有 Agent 间通信走 Pydantic State，无自然语言对话** —— 未来替换 LLM 供应商
   （OpenAI → 智谱）只需改 prompt 模板，State Schema 不动
5. **Schema 双层架构（核心层固定 + 扩展层动态）** —— 未来 SaaS 化按行业卖
   "扩展模板包"有现成的扩展点
6. **StreamBridge 抽象层（§五.Y 约束 4）** —— MVP 用内存实现，生产化平滑切 Upstash Redis / RabbitMQ，
   SSE 端点和 Worker 进程解耦，多实例横向扩展时不用重写。借鉴自 DeerFlow `runtime/stream_bridge/`

### Provider 模式统一架构（**答辩叙事重点**）

> 本节说明 SurveyTool、HybridSearch、企业 KB 接入在架构上的统一设计思路。
> **MVP 已实现的 Provider 抽象**（2 个实证）：
> - `SearchProvider` — 代码在 `backend/services/search/providers/`
> - `SurveyDistributor` — 代码在 `backend/services/survey/distributors/`
>
> **生产化路线图占位**（本期 0 代码）：
> - `KnowledgeBaseProvider`

**核心思路**：所有外部数据采集能力都收敛为可插拔的 Provider，CollectorAgent 只与抽象接口通信，不感知底层实现；失败时按策略降级，全过程进 `trace_log`。

```
CollectorAgent
  ├── web_search()            → SearchProvider（Protocol）
  │     ├── TavilyProvider          ← 主，AI 优化的搜索
  │     └── SerpApiProvider         ← 备，Google 搜索 fallback
  │         降级策略：Tavily 429/超时 → 自动切 SerpApi
  │         全失败：抛 SearchUnavailableError → LangGraph 节点 retry
  │
  ├── fetch_page()            → (内置，Playwright；非 Provider)
  ├── app_review_fetch()      → (内置；非 Provider)
  │
  ├── SurveyTool              → SurveyDistributor（Protocol）
  │     └── SimulatedDistributor  ← MVP 唯一实现（LLM 模拟）
  │         未来可替换为:
  │         TypeformDistributor / WenjuanxingProvider / 企业样本池
  │
  └── KnowledgeBaseProvider   ← 生产化占位（本期不实现）              [路线图]
        未来可实现:
        ConfluenceProvider / SharePointProvider /
        NielsenProvider / GleanProvider / SQLProvider
```

**`SearchProvider` Protocol（MVP 已实现）**：

```python
class SearchProvider(Protocol):
    name: str                                          # "tavily" / "serpapi"
    def search(self, query: str, max_results: int = 5) -> list[SourceCitation]: ...
    def is_available(self) -> bool: ...                # 按 env key + 依赖库探测
```

- `HybridSearchTool` 编排器按 `[TavilyProvider, SerpApiProvider]` 顺序串行降级
- 每次降级写入 `trace_log`（`stage="search.fallback"`，含 failed_provider / reason / next_provider）
- 返回的每条 `SourceCitation` 自带 `provider` 字段，溯源面板可显示"该证据来自哪个 search provider"
- CollectorAgent 调用方式不变：`results = web_search(query, max_results=5)`

**`SurveyDistributor` Protocol（MVP 已实现）**：

```python
class SurveyDistributor(Protocol):
    def distribute(self, questionnaire, target_personas, sample_size) -> DistributionHandle: ...
    def collect_responses(self, handle, timeout_seconds) -> list[SurveyResponse]: ...
```

- 签名是生产级的，MVP 只切换实现层（`SimulatedDistributor`）
- 替换为真实问卷平台时，CollectorAgent 代码不动，只换 Distributor 实现

**`KnowledgeBaseProvider` 架构占位（生产化路线图）**：

```python
class KnowledgeBaseProvider(Protocol):  # 本期不实现
    def search(self, query: str, filters: dict) -> list[KBDocument]: ...
```

生产环境中，CollectorAgent 可通过 `internal_kb_search()` 将企业内部知识（Confluence、SharePoint、历史报告、付费数据库）与公开 web search 并列形成混合检索结果，统一写入 `SourceCitation` 溯源体系。

**答辩话术建议**：
> "我们用 Provider 模式统一了所有外部数据采集能力。演示中 `web_search` 内部走 `SearchProvider` 抽象——Tavily 主、SerpApi 备，失败自动降级，每条溯源都标记来自哪个 provider；`SurveyDistributor` 同样的形态，`SimulatedDistributor` 是 MVP 实现，替换为 Typeform 零改动。再加上 `KnowledgeBaseProvider` 占位，未来企业 Confluence、SharePoint、付费数据库可以以同一形态接入，让公开调研、用户声音、内部知识并列进溯源体系。"

**本期硬约束（不得违反）**：
- 主流程 / 报告页 / API **不**暴露企业 KB 上传入口
- Settings 页**不**加"数据源管理"功能
- 演示中**不**暗示 KB 接入已实现（只讲架构可插拔）
- HybridSearch 不做"并发查多源 + 结果融合"，只做串行降级（future work）

---

## 十一-quater、演示模式 / Demo Mode

> **目的**：演示日 OpenAI / Tavily / Neon / Railway 任一抽风时，评委仍能完整体验产品全流程；同时降低评委试用的 token 成本（每次点击 = 0 美元）。
>
> **设计原则**：**纯前端静态回放，零后端调用**。与真实 LangGraph 流程并存、互不干扰。

### 11Q.1 入口

demo 有**两个入口**，都不藏：

1. **全站顶部导航栏 `[▶ 30 秒demo演示]`**——任何页面都能一键直跳 `/demo/scoping`
2. **`/tasks/new` NL 关键词触发**——用户在 NL 中写「直接生成 / 跳过 / 不要大纲 / directly / skip / no plan」等，按钮自动切换为「直接分析」，提交后跳 `/demo/scoping`（MVP 阶段；后端就绪后接真实直跑路径）

> **不藏 demo 的理由**：评委要看的就是"端到端产品体验"，demo 路径**就是**最完整的端到端，不是降级版。

### 11Q.2 路由与体验脚本

demo 路径走独立 route 前缀 `/demo/*`，**绝对不复用** `/tasks/new` / `/tasks/{id}` / `/reports/{id}` 的真实 route——避免 fixture 数据污染真实任务。

```
[点击「30 秒看完整演示」]
  ↓
/demo/scoping              （预填 NL + 竞品 chip + 大纲，1.5s 自动「确认 → 开始分析」）
  ↓
/demo/run                  （伪 DAG 动画 — 预录的 trace 一条条按时间戳回放，
                            ~20-30s 走完 4 个 Agent，每节点完成有视觉反馈）
  ↓
/demo/report               （预先生成好的真报告 — 核心 4 章 + 2-3 个扩展章
                            溯源面板 / PDF 导出 / PPTX 导出 / 字段展开 全功能可用）
```

每个 demo 页面**右上角固定一个"演示样例"水印徽标**，hover 显示 tooltip：「本路径为预录回放，用于网络/API 异常时的兜底体验。点这里走真实任务」→ 跳 `/tasks/new`。

### 11Q.3 数据形态

所有 fixture 落在前端 `src/lib/mocks/demo/`：

| 文件 | 内容 |
|---|---|
| `scope.json` | 完整 `TaskScopeContract`（含 user_brief / clarifications / dimensions / competitors） |
| `trace.json` | DAG 回放脚本：`[{ts_offset_ms, agent, event, payload}, ...]`，~30 条 |
| `report.json` | 完整报告渲染数据（核心 4 章 + 2-3 扩展章 + sources + cross_analysis） |
| `sources.json` | `SourceCitation` 列表，每条都有真 URL（指向公开网页），溯源点击能真正打开 |

**演示案例选择**：建议用**汉高场景的 3 个真实日化竞品**（SK-II / 资生堂 / 雅诗兰黛）的「会员体系与 KOL 策略」分析——
- 评委 / 老师容易共鸣
- 跟 §十四 访谈场景对齐，体现"贴合真实业务"
- 报告内容由项目组**预先用真实 LangGraph 跑过一次**再截图固化（不是手写编造）

### 11Q.4 验收

- ✅ 完全离线可演示（拔网线 → 浏览器开 demo → 全流程跑完）
- ✅ 三个 demo 页面之间的跳转 ≤ 总时长 30s
- ✅ 报告页所有交互（溯源 / 展开 / 导出）真实可用，不是图片
- ✅ 水印明确标注，**绝不**伪装成真实任务
- ✅ 不污染真实任务路由的代码与数据

### 11Q.5 工程量估算

约 **2-3 个工作日**（前端独立完成，与后端开发并行）：
- 1 天：3 个 demo 页面 + 水印 + 路由
- 1 天：fixture 数据生成（先手写一版，后端跑通后用真数据替换）
- 0.5-1 天：联调 + 视觉打磨

### 11Q.6 与评分项的映射

| 评分项 | demo 模式如何加分 |
|---|---|
| 业务价值 20% | "30 秒看完整产品"对评委的第一印象远超"等 5 分钟看真实跑" |
| 多 Agent 协作 35% | demo 报告就是真实跑的产物截图，溯源与 Schema 完整性照样能展示 |
| 答辩材料 10% | 演讲稿可以"先放 demo 跑完，再现场跑一遍真实"——双保险 |
| 技术深度 25% | demo 不会"加分"，但能确保前面三项不会**因为现场翻车而丢分** |

### 11Q.7 路由职责边界 / Route Isolation Contract（🔴 强约束）

为防止"演示样例污染真实路径"——例如用户在 `/tasks/new` 输入「研究 AI IDE 市场」，立项页却回退到护肤大纲——以下规则**不可违反**：

| 路由前缀 | 数据来源 | 大纲内容 | 备注 |
|---|---|---|---|
| `/demo/*` | **仅** `frontend/src/lib/mocks/demo/*.json` fixture | 永远是预制场景（当前为 SK-II/资生堂/雅诗兰黛），与用户实时输入无关 | 顶部导航栏「30 秒demo演示」入口 |
| `/tasks/new/*` 与 `/tasks/{id}` | **仅** ScopingAgent / DAG 4 Agent 真实产物 | 必须根据用户 NL 动态生成 | 后端未就绪时降级为"空骨架"，**绝不**回退到 demo fixture 或任何与领域绑定的硬编码 mock |

**强约束**：
1. `frontend/src/lib/mocks/demo/` 下的任何文件**只能**被 `/demo/*` 路由 import；CI 应有 ESLint rule / 自定义 import guard 防止越界（Week 1 加）
2. 真实路径在 ScopingAgent 未接通时的合规降级形态：
   - 4 个核心维度照常渲染（核心层与领域无关，[scope-contract.ts buildCoreDimensions()](../frontend/src/lib/mocks/scope-contract.ts) 可复用）
   - 扩展维度区**留空**，渲染一个温和提示："ScopingAgent 连线中，请使用「+ 增加自定义维度」手动补充"
   - 竞品 chip 区**留空**，渲染提示："使用 [+] 手动添加已知竞品"
   - **绝不**渲染任何与领域绑定的占位扩展（"会员体系" "KOL 矩阵" 等）
3. `/tasks/new` 页的示例 brief 快填 chips（Trae / 飞书 / 抖音）只填充 NL 文本，**不预先 mock 出对应大纲**——用户提交后仍走真实路径的空骨架降级，避免"点示例 → 看到护肤大纲"的错位
4. 真实 ScopingAgent 上线后，本节"未就绪降级"规则失效，但**路由隔离规则（第 1 条）永久生效**

**违反此约束的代价**：演示日评委点示例 chip → 看到答非所问的大纲 → 多 Agent 协作的可信度被打折扣（直接影响"业务价值 20%"与"AI 协作 35%"两大评分项）。

## 十二、3 周迭代计划

> **进度状态说明**：下方复选框为「计划项是否已落地」的勾选；`[x]`=完成、`[~]`=部分、`[ ]`=未做。
> 实时、细粒度的进度真相源是 [claude-progress.txt](../claude-progress.txt) 的系统级进度表，本节随重要里程碑同步勾选即可。最后核对：2026-05-28（读代码盘点）。

### Week 0.5 (0.5 周): 架构落地与脚手架
- [x] **创建项目入口文档**：`CLAUDE.md` + `AGENTS.md`（指引所有编程 Agent 读取 PRD、架构图、Agent 协议、Schema 文档）
- [x] Repo 初始化（monorepo: `frontend/` + `backend/`）
- [ ] Railway 项目搭建 + Neon + Upstash 接入（云端部署未验证；本地 Postgres 已迁移到 head、Redis 依赖已装）
- [x] FastAPI + LangGraph 骨架，跑通 Hello World DAG
- [x] Next.js + shadcn/ui 骨架，跑通登录页 UI
- [x] 数据库 Schema 落库（Alembic 迁移）
- [x] 关键 Pydantic Schema 定义（章节七的 Schema 转代码）

### Week 1 (1 周): Agent 单体开发
- [x] CollectorAgent：搜索 + 网页抓取 + 输出 RawCollectionResult
- [x] AnalystAgent：原始数据 → StructuredProfile
- [x] WriterAgent：StructuredProfile → ReportDraft（带引用）
- [x] QAAgent：检查 + 输出 issues
- [~] 每个 Agent 单元测试（mock LLM）（已有 workflow/scoping/survey/scraper/auth 测试，未逐 Agent 拆单测）
- [x] LangGraph DAG 串起来（无反馈闭环版本）（已超出：直接含 QA→collect 反馈闭环）

### Week 2 (1 周): 联调 + 反馈闭环 + 前端联动
- [x] 反馈闭环逻辑（QA → 打回 → 重跑 → 改善验证）（后端 LangGraph 条件边，retry≤3）
- [x] SSE 实时推送 DAG 状态（StreamBridge / RedisStreamBridge + `/stream` 路由；前端尚未接）
- [ ] 前端 DAG 可视化（用 React Flow 或 D3）
- [ ] 报告页交互（溯源面板、字段展开）
- [x] PDF 导出（标准库实现，返回真实字节）
- [x] PPTX 导出（用 python-pptx）
- [ ] 端到端跑通：3 个真实竞品的演示案例

### Week 0.5 (0.5 周): 答辩准备
- [ ] 演示视频录制
- [ ] 架构图 / Agent 协议文档 / README 完善
- [ ] 演示稿（含关键指标量化）
- [ ] 预案：演示时网络/API 失败的兜底（预录跑过的样本）
- [ ] 与汉高战略部实习生最后一次场景对齐

### 风险与缓冲

| 风险 | 影响 | 缓解 |
|---|---|---|
| OpenAI API 速率限制 | 演示时卡死 | 实现请求队列 + 关键演示用预跑结果回放 |
| Tavily/SerpApi 抓取失败 | 信源不足 | 准备 fallback 到 LLM 直接生成（带"模拟"标记）|
| PPTX 生成质量不达预期 | 汇报体验差 | 提前 1 周做 PPTX POC，确认排版可行 |
| LangGraph 学习曲线 | 进度延迟 | Week 0.5 集中跑通官方示例 + checkpointer |
| 3 周时间紧 | 功能砍不动 | P0 先形成稳定主链路，P1 在答辩前收口；若时间紧，只压缩 P1 的样本量/展示深度，不取消 P1 能力；P2 不做 |
| 演示日多评委同时点 | 单实例 FastAPI 卡 SSE 长连接 | 临时把 Railway 从 Hobby 升到 Pro（workers 调到 8-16）+ 预置 3 个评委账号 + `/reports/demo` 不登录直接看的样例报告 + **SSE 心跳 + Last-Event-ID 幂等重连**（§五.Y 约束 1，断线即可恢复，不依赖客户端记忆进度）|

---

## 十三、验收标准（对应评分维度）

### 多 Agent 协作与输出可信度 (35%)
- ✅ 4 个 Agent 各司其职，职责无重叠（代码注释 + 文档说明）
- ✅ LangGraph DAG 可在前端可视化，所有节点状态可追溯
- ✅ Agent 间通过 Pydantic State 通信（无自然语言对话）
- ✅ 反馈闭环现场可触发：构造缺失数据 → QA 打回 → 重跑后字段完整
- ✅ **核心层 Schema** 100% 输出符合（功能树/定价/画像/SWOT），字段完整率 ≥95%
- ✅ **扩展层** 按 TaskScopeContract 协商生成，每条结论同样强制带 `source_ids`
- ✅ 每条结论（核心层 + 扩展层）可一键溯源到原始 URL+片段

> **评分项备 answer**：评委可能问"扩展层是不是绕过了'预定义 Schema'要求"——回答：核心层 4 套 Schema 就是预定义对象，QA 对核心层缺失字段硬打回（演示时可触发）；扩展层是评分卡 25% 项里明文提到的"动态 Schema 演化"加分项的具体实现，与"严格符合预定义 Schema"不冲突。
>
> **追问备 answer**：若评委进一步问"扩展层会不会被 AI 无限发散、失去 Schema 严肃性"——回答：扩展层有**双层数量约束**——ScopingAgent 单次最多建议 **4 个**（`source="ai_suggested"`，写进 TaskScopeContract 不变式 + prompt 双重保险），保证 AI 自主性可控；用户手动添加的扩展维度（`source="user_added"`）不设上限，把"模型保守 + 人类自由"显式分离，正是 35% 评分卡里"Agent 间通信协议清晰"和 20% "人工介入修正易用直观"两项的具体落地。

### 技术深度与工程完整度 (25%)
- ✅ 端到端可访问：登录 → 创建 → **对话式立项** → 跑 → 看报告 → 导出，全链路无中断
- ✅ 每个 Agent 的 Prompt / 输入 / 输出 / Token / 延迟 在 Trace 页可查
- ✅ 幻觉抑制策略明确：强制引用 + QA 事实校验 + 多源交叉
- ✅ 异常处理：网络失败重试、API 限流降级、节点失败标记并继续
- ✅ **动态 Schema 演化**已落地：TaskScopeContract + 双层 Schema，可演示同一套代码跑日化 / SaaS / 工业品三类截然不同的报告
- ✅ **自适应任务拆分**已落地：Collector 按 `dimension.intent` 做 query 改写，Analyst 按 `layer` 走差异化抽取器
- ✅ P1 增强能力答辩前完成：pgvector 历史报告语义检索、Agent 决策时间轴、应用商店真实评论 provider、多语言报告

### 业务价值与产品体验 (20%)
- ✅ 5-10 分钟出报告 vs 人工 1-2 天（演示时计时对比）—— 注意：对话式立项阶段计入"分析时间"还是分开报告？演讲时建议分开，因为这是用户感知的"主动配置"时间，不算等待
- ✅ 自动覆盖 ≥5 信息源（数量统计在报告底部展示）
- ✅ **Schema 按场景动态生成**（演示换行业不用改代码，演示同时跑日化 + SaaS 对比说明性最强）
- ✅ 交互流畅：溯源、导出、回放、**人工介入修正** 主路径 ≤3 次点击
- ✅ **入口体验贴合真实工作流**：用户用自然语言描述需求，AI 协商出本次任务的维度大纲，对比"勾选预设维度"的填表式入口，更接近"和分析师同事讨论"的真实交互

#### 业务闭环量化指标（claim 级，§7.9 为计量单元；三指标严格区分不可混）

> **claim = 报告中任何带 `source_ids` 的节点**（§7.9）。`T = claim 总数`。一律 claim/字段级计算，**不用字数**（字数失真）。

| 指标 | 公式 | 阶段 | 优先级 |
|---|---|---|---|
| **分析耗时** | `completed_at − started_at` | 生成时（自动） | P0 |
| **字段覆盖率** | 已填核心必填字段 / 应填核心字段 | 生成时 | P0 |
| **需求覆盖率** | 已完成维度 / TaskScopeContract.dimensions(enabled)（维度"完成"=claims 填全+有源+无 blocker） | 生成时 | P1 |
| **引用覆盖率** | `source_ids` 非空的 claim / T（= 有没有挂 source） | 生成时 | P0 |
| **来源支撑率** | QA 判定"来源确实支撑该结论"的 claim / T（= 源能不能证明） | 质检（自动） | P1 |
| **信息源类型覆盖率** | 命中的 `SourceCitation.category` 数 / 5（官方/媒体/用户反馈/技术社区/商业） | 生成时 | P1 |
| **无效来源率** | `valid=false` 的 source / source 总数 | 生成时 | P1 |
| **人工修正率** | 被人工修改的 claim / T（按 `correction_type` 拆 5 类） | 人工闭环 | P0 |
| **人工确认准确率** | 加权 `(正确 + 0.5×部分正确) / 抽检 claim 数`（= 事实对不对） | 人工闭环 | P0 |
| **重跑率** | 用户要求重新生成的模块数 / 总模块数 | 人工闭环 | P1 |

- **三指标递进关系**（答辩核心叙事）：`引用覆盖率`(有源) ⊇ `来源支撑率`(源有效) ⊇ `人工确认准确率`(事实对)——回答评委"溯源到底可不可靠"
- **真·准确率回算** = `1 − (事实修正 claim / T)`；表述优化 / 结构调整不计入"AI 出错"
- 指标随人工编辑 / 复核实时更新，沉淀为下一轮 Prompt / Source 策略 / Schema 优化依据（支持"运营迭代"评分点）
- **P0 首批交付 = MVP-5**：分析耗时 / 字段覆盖率 / 引用覆盖率 / 人工修正率 / 人工确认准确率，保证主链路尽早可演示
- **P1 答辩前必达**：来源支撑率 / 信息源类型覆盖率 / 无效来源率 / 重跑率 / 修正类型 5 分类细分 / AI 自评 vs 人工验证对比块，必须在报告页和导出摘要页可见

### 代码质量与文档 (10%)
- ✅ Monorepo 结构清晰，TS/Python 各自 lint+test
- ✅ README + 架构图 + Agent 协议文档 + Schema 文档 + 部署说明齐全
- ✅ Git 提交规范（conventional commits），分支：main/dev/feature-*
- ✅ TRAE / Claude Code 使用痕迹（commit message 引用 + 文档记录）

### 合规、材料与答辩 (10%)
- ✅ 信息采集合规：尊重 robots.txt（采集 Agent 内置检查）
- ✅ 模拟数据明确标识"AI 生成模拟"
- ✅ 提交材料：方案文档（本 PRD）+ 演示视频 + 代码库 + 部署链接
- ✅ 答辩演示稿覆盖：架构 / 创新点 / 闭环演示 / 指标



## 十四、关键文件路径预告（交给开发 Agent）

待开发 Agent 实现时，建议项目结构：

```
competitor_analysis/
├── frontend/                         # Next.js
│   ├── app/(auth)/login/
│   ├── app/tasks/new/
│   ├── app/tasks/[id]/page.tsx       # 进行中 DAG 页
│   ├── app/reports/[id]/page.tsx
│   └── components/dag-viewer/
├── backend/                          # FastAPI
│   ├── routers/auth.py
│   ├── routers/tasks.py
│   ├── routers/reports.py
│   ├── agents/
│   │   ├── collector.py
│   │   ├── analyst.py
│   │   ├── writer.py
│   │   └── qa.py
│   ├── graph/
│   │   ├── workflow.py               # LangGraph DAG 定义
│   │   └── state.py                  # WorkflowState Pydantic
│   ├── schemas/
│   │   ├── feature_tree.py
│   │   ├── pricing.py
│   │   ├── persona.py
│   │   └── report.py
│   ├── services/
│   │   ├── search.py                 # Tavily/SerpApi wrapper
│   │   ├── scraper.py                # Playwright
│   │   └── exporter.py               # PDF/PPTX
│   └── db/
│       ├── models.py                 # SQLAlchemy
│       └── migrations/
├── packages/
│   └── shared-schemas/               # TS+Python 共享 Schema (可选)
├── docs/
│   ├── architecture.md
│   ├── agent-protocol.md
│   └── deployment.md
└── README.md
```

