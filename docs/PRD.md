# PRD: AI 驱动的竞品分析 Agent 协作系统

> **文档性质**: 产品需求文档（PRD），交付给开发 Agent 拆任务用
> **版本**: v1.8
> **日期**: 2026-05-27
> **作者**: PM (Claude) + 项目负责人
>
> **v1.1 修订说明**（2026-05-23）：基于汉高战略部实习生反馈与比赛评分卡复核，引入**对话式立项 + 双层 Schema** 架构。固定 Schema（功能树/定价/画像/SWOT）保留为"核心层"满足比赛"严格符合预定义 Schema"评分项；新增"扩展层"由 AI 与用户协商动态生成，解决"维度因行业而异、无法预先穷尽"的真实痛点。详见本次修订设计草案 [plans/2026-05-23-dynamic-outline-scoping-design.md](../plans/2026-05-23-dynamic-outline-scoping-design.md)。影响章节：§四 / §六 / §七 / §九 / §十三 / §十四。
>
> **v1.2 修订说明**（2026-05-24）：显式声明 MVP 不做的事（避免开发 Agent over-engineering），并补一节"未来生产化路径"作为答辩材料。**不改动任何业务逻辑、Agent 设计或 Schema**，仅新增 §十一-bis Non-Goals、§十一-ter 未来生产化路径，§十二 风险表追加一行演示日并发兜底。详见 [plans/2026-05-24-prd-non-goals-and-future-scale.md](../plans/2026-05-24-prd-non-goals-and-future-scale.md)。
>
> **v1.3 修订说明**（2026-05-25）：新增 §十一-quater **演示模式（Demo Mode）**——纯前端静态回放路径，与真实 LangGraph 流程并存。同时把 §十一-bis 那行 `/reports/demo` 占位升级为完整规格。目的：演示日 API/网络抽风时仍可完整走完产品流程，并降低评委试用的 token 成本。**不改动任何 Agent 设计 / Schema / DAG 逻辑**，仅新增前端预录路径与对应 fixture。同步在 §九 前端线框图标注 demo 入口按钮。
>
> **v1.4 修订说明**（2026-05-25）：新增 **ScopingAgent**（第 5 个 Agent，DAG 外的对话式立项主语）填补 v1.1 留下的"TaskScopeContract 无人生成"漏洞。统一 NL 入口支持**三种意图模式**（A 列表式 / B 意图式 / C 混合式），混合模式 P0；§八 API 8.5 改名为 Scoping，原 `/api/competitors/suggest` 合并进 `/api/scoping/draft`；§七 7.0 TaskScopeContract 加 `intent_mode` 与 `scoping_rationale`，`competitors` 升级为 `list[CompetitorCandidate]` 保留 source 信息；§十 DB schema 加 `scoping_drafts` 表保留对话历史。详见 [plans/2026-05-25-prd-v1.4-scoping-agent-and-modes.md](../plans/2026-05-25-prd-v1.4-scoping-agent-and-modes.md)。影响章节：§四 / §六 / §七 / §八 / §九 / §十 / §十一 / §十一-quater / §十三。
>
> **v1.5 修订说明**（2026-05-25）：把 PRD 对齐到当前前端实际设计——`/tasks/new` 简化为**纯 NL 单一输入框**（移除"可选竞品 chip 区"），已知竞品由 ScopingAgent 从 NL 中提取；用户在 `/tasks/new/scoping` 立项页才能手动增删竞品。新增 **direct 模式**：NL 中含"直接生成 / 跳过 / 直接分析"等关键词时跳过 scoping 页，直接进入分析（演示走 `/demo/scoping`）。**演示入口迁移**：原 `/tasks/new` 顶部并排的"30 秒看完整演示"按钮已迁到全站顶部导航栏，使任务创建页只保留一个聚焦动作。`/tasks/new` 增加 3 个示例 brief 快填 chips（仅填充 NL，非竞品输入）。**不改动任何 Agent 设计 / Schema / DAG 逻辑**，仅同步入口形态。影响章节：§四 / §六（ScopingRequest 输入来源说明）/ §九（页面 1a 线框图）/ §十一-quater 11Q.1。
>
> **v1.5.1 修订说明**（2026-05-26）：明确 **`/demo/*` 与 `/tasks/new/*` 的路由职责边界**（新增 §十一-quater 11Q.7）。背景：Stage 1 前端临时让 `/tasks/new/scoping` 在 ScopingAgent 未接通时回退到护肤 mock（`buildSkincareMockContract`），导致"输入 AI IDE 得到护肤大纲"的演示翻车风险。新边界：`mocks/demo/*` 只能被 `/demo/*` 路由消费；真实路径**绝不**回退到任何与领域绑定的硬编码 mock，ScopingAgent 未就绪时应表现为"连线中"空骨架，让用户手动构造扩展维度。影响章节：§四 [3] / §六 5.0（未就绪行为）/ §十一-quater（11Q.7 新增）。
>
> **v1.6 修订说明**（2026-05-26）：**SurveyTool 架构纳入 PRD**。新增 §七 7.8 Survey 系列 Schema（Questionnaire / TargetPersona / DistributionHandle / SurveyResponse / SurveyEvidence / SurveyInsight / SurveyResult）；§七 7.6 `SourceCitation.type` 枚举扩展（新增 `published_survey` / `public_review` / `ai_simulated`，废弃 `simulated_survey`）；§六 5.4 QAAgent 检查清单增 SurveyInsight 校验 4 条；§六 WorkflowState 加 `survey_results` 字段；§六 5.1 CollectorAgent 工具集加 SurveyTool；§十一-ter 新增"Provider 模式统一架构"小节（SurveyDistributor + KnowledgeBaseProvider）。**RAG / 企业 KB 本期不实现**，仅在 §十一-ter 作为路线图占位。详见 [plans/2026-05-26-survey-tool-design.md](../plans/2026-05-26-survey-tool-design.md) 与 [plans/2026-05-26-survey-tool-plan-revision.md](../plans/2026-05-26-survey-tool-plan-revision.md)。
>
> **v1.7 修订说明**（2026-05-26）：**`web_search` 升级为 HybridSearch Provider 模式**。§六 5.1 `web_search` 工具描述改为"内部走 `SearchProvider` 抽象，Tavily 主、SerpApi 备，降级写 trace"；§六 WorkflowState trace 命名表追加 `search.invoke` / `search.fallback` / `search.exhausted`；§七 7.6 `SourceCitation` 加 `provider` 字段（记录产出该引用的 search provider 实现）；§十一-ter Provider 模式架构图升级，`web_search` 从"内置"升为 `SearchProvider` 实证，实现层示例追加 `TavilyProvider` / `SerpApiProvider`。**Provider 模式实证从 1 个（SurveyDistributor）增至 2 个（+SearchProvider）**，答辩叙事更完整。详见 [plans/2026-05-26-hybrid-search-provider.md](../plans/2026-05-26-hybrid-search-provider.md)。
>
> **v1.8 修订说明**（2026-05-27）：**LLM 选型按 Agent 锁定**。新增 §五.X 模型选型决策表（Collector=Gemini 2.5 Flash / Analyst+Writer=DeepSeek V4 Pro / QA=gpt-4o-mini，演示周成本上限 ~$3）；§五 部署拓扑表 LLM 行同步更新；§六 5.1–5.4 各 Agent 起首加"使用模型"行；§十一-bis Non-Goals 补"MVP 不调用 embedding API（pgvector schema 字段保留为 P1 准备）"，并把"国内合规 LLM 替换"从 Non-Goals 移除（MVP 已部分国产化）；§十一-ter 第二阶段「合规」行同步更新为 MVP 已用 DeepSeek + 生产化扩展国产 Provider。**选型原则**：成本 × 能力同时兼顾，不追求最强（Analyst 用能力 86 / 成本 $0.21 的 DeepSeek V4 Pro 替代能力 90 / 成本 $1.26 的 gpt-4.1）。详见 [plans/2026-05-26-prd-open-questions.md](../plans/2026-05-26-prd-open-questions.md)。

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
[1] 用户登录（邮箱验证码 OAuth）
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
      (c) 1-3 个补充澄清问题（可跳过）
      (d) intent_mode 标签 + rationale 摘要（顶部折叠面板，默认收起）
    用户编辑：
      - 竞品 chip：可增删（包括踢掉 AI 推荐的），可点「让 AI 再推荐几个」补
      - 核心章节（🔒 功能树 / 定价模型 / 用户画像 / SWOT）可改名 / 改意图 / 调顺序，不可删
      - 扩展章节（✏️ 任务相关维度）可改名 / 改意图 / 调顺序 / 删除 / 自定义新增
      - 「重新生成大纲」按钮 = 带当前编辑过的章节 + 竞品 + 澄清回答回到 ScopingAgent 再生成
    用户点「确认 → 开始分析」时，大纲 freeze 成 TaskScopeContract（见 §七 7.0）

    ⚠️ 路由职责边界（v1.5.1，详见 §十一-quater 11Q.7）：本页**仅**渲染
    ScopingAgent 真实产物；ScopingAgent 未接通时降级为"4 核心 + 空扩展 + 空
    竞品 + 连线中提示"骨架，绝不回退到任何与领域绑定的硬编码 mock，也不读取
    /demo/* fixture——这是为了避免"输入 AI IDE 看到护肤大纲"的演示翻车。
    ↓
[4] 启动 Agent 协作（任务运行页 /tasks/{id}）：
    实时显示 DAG 进度（哪个 Agent 在跑、跑到哪一步、Trace 可点开）
    采集 Agent → 分析 Agent → 撰写 Agent → 质检 Agent
                                              ↓
                            （质检不通过，打回上游 Agent 重做）
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

> **v1.0 → v1.1 关键变化**：原 [2] 步的 A/B/C 三选项入口被合并为"NL 输入 + 可选 chip"的单一入口；原 [3] 步"维度勾选"被完全替换为"对话式立项"。背景见 §一 v1.1 修订说明与 [plans/2026-05-23-dynamic-outline-scoping-design.md](../plans/2026-05-23-dynamic-outline-scoping-design.md)。
>
> **v1.3 → v1.4 关键变化**：[2] [3] 步骤的"AI"明确为 **ScopingAgent**（§六 5.0 新增）；统一 NL 入口支持 3 种意图模式（列表 / 意图 / 混合），ScopingAgent 自动判别；竞品列表升级为 `list[CompetitorCandidate]` 保留 source 信息，AI 推荐项在 UI 视觉区分；scoping 页加「让 AI 再推荐几个」按钮。背景见 §一 v1.4 修订说明与 [plans/2026-05-25-prd-v1.4-scoping-agent-and-modes.md](../plans/2026-05-25-prd-v1.4-scoping-agent-and-modes.md)。
>
> **v1.4 → v1.5 关键变化**：[2] 步彻底简化为**单一 NL 输入框**，移除"可选竞品 chip 区"——已知竞品全部交给 ScopingAgent 从 NL 中提取；用户增删竞品只发生在 [3] 立项页。新增 **direct 模式** NL 关键词快捷路径（跳过 [3]）。/tasks/new 页内"30 秒演示"按钮迁到顶部导航栏。背景见 §一 v1.5 修订说明。

### 用户旅程关键体验点

| 节点 | 用户期望 | 设计承诺 |
|---|---|---|
| 等待期 | 不焦虑 | 实时 DAG 可视化 + Agent 当前正在做什么的中文描述 |
| 看报告 | 快速理解 | 顶部摘要 + 功能对比矩阵 + SWOT + 详情可展开 |
| 不信任结论 | 一秒验证 | 每条结论旁有"溯源"小图标，点击展开原始数据片段+URL |
| 想修改 | 不重跑全流程 | 编辑单个字段 → 仅触发涉及该字段的 Agent 重跑 |

---

## 五、系统架构

### 总体架构图（文字描述）

```
┌────────────────────────────────────────────────────────┐
│  前端 (Next.js, Railway)                                │
│  - 登录 / 任务创建 / DAG 可视化 / 报告交互 / 导出       │
└──────────────────────────┬─────────────────────────────┘
                           │ REST + SSE
┌──────────────────────────▼─────────────────────────────┐
│  后端 API (FastAPI, Railway)                            │
│  - Auth / 任务调度 / SSE 推送 / 报告导出（PDF/PPTX）    │
└────────┬──────────────────────────────┬─────────────────┘
         │                              │
┌────────▼────────────┐    ┌────────────▼────────────────┐
│  LangGraph Engine   │    │  外部服务                    │
│  - 4 Agent DAG      │    │  - OpenAI API (GPT-4o/4.1)  │
│  - Checkpointer→PG  │    │  - Tavily / SerpApi (搜索)   │
│  - 反馈闭环逻辑      │    │  - Playwright (网页抓取)     │
└─────────┬───────────┘    └─────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────┐
│  数据层                                                  │
│  - Neon Postgres (3GB free): 业务数据+pgvector+Trace   │
│  - Upstash Redis (free): 任务队列+SSE+Agent中间状态     │
└────────────────────────────────────────────────────────┘
```

### 部署拓扑

| 服务 | 平台 | 计费 |
|---|---|---|
| Frontend (Next.js) | Railway | Hobby ~$3/月 |
| Backend (FastAPI) | Railway | Hobby ~$3-5/月 |
| Postgres + pgvector | Neon | Free Forever (3GB) |
| Redis | Upstash | Free (10K commands/天) |
| LLM | Gemini 2.5 Flash + DeepSeek V4 Pro + gpt-4o-mini（按 Agent 分配，见 §五.X） | 演示周约 $3 |
| Search API | Tavily Free / SerpApi Free | 免费额度 |

### 五.X 模型选型决策表（v1.8 新增）

按 Agent / task 锁定 LLM 模型，开发期写死在 `backend/settings.py`，不暴露给终端用户切换。

| Agent | 模型 | 输入 / 输出（USD/1M tokens） | 7 天演示成本 | 能力分 | 选择理由 |
|-------|------|----------------------------|-------------|--------|---------|
| CollectorAgent | `gemini-2.5-flash` | $0.30 / $2.50 | ~$0.28 | 78 | 1M 上下文塞检索结果；tool use 稳定；Google 索引内核做 query 改写参考 |
| AnalystAgent | `deepseek-v4-pro` | $0.435 / $0.87 | ~$0.21 | 86 | 推理强 + 384K 输出容量；成本仅 gpt-4.1 的 1/6（2026-05 永久 75% 降价后） |
| WriterAgent | `deepseek-v4-pro` | $0.435 / $0.87 | ~$0.21 | 88（中文） | 中文长报告自然度高；与 AnalystAgent 同模型简化 prompt 协调 |
| QAAgent | `gpt-4o-mini` | $0.15 / $0.60 | ~$0.10 | 75 | JSON 结构化检查任务简单，便宜款够用 |

**演示周（7 天 × 5 任务/天）总成本上限**：~$3（含 20% 缓冲）；单次任务 token 消耗假设 100K input + 20K output。

**选型原则**："成本 × 能力同时兼顾，不追求最强"——例如 Analyst 不用 gpt-4.1（能力 90 / 成本 $1.26），改用 DeepSeek V4 Pro（能力 86 / 成本 $0.21），**用 1/6 的钱买 95% 的能力**。

**为什么不全用 DeepSeek**：CollectorAgent 一格保留 Gemini 2.5 Flash —— 因为它的 1M 上下文 + Google 索引内核做 query 改写参考时质量更好；QAAgent 用 gpt-4o-mini 是因为 OpenAI SDK 与 DeepSeek 兼容 SDK 同源，跨家协调成本最低。

**SDK 与配置**：
- DeepSeek 兼容 OpenAI SDK（base_url=`https://api.deepseek.com/v1`），与 gpt-4o-mini 共用 `openai` Python 包
- Gemini 用 `google-genai` SDK
- 环境变量：`OPENAI_API_KEY` / `GEMINI_API_KEY` / `DEEPSEEK_API_KEY`（密钥管理见 [docs/security.md](security.md)）

**未来路径**：见 §十一-ter 第二阶段「合规」行——MVP 已部分国产化（Analyst+Writer），生产化阶段补充智谱 GLM / 阿里通义 / MiniMax 多 Provider。

---

## 六、多 Agent 设计（核心）

> **v1.4 架构**：系统总共 5 个 Agent，分两层——
> - **ScopingAgent**（5.0）：在主 DAG 启动**之前**跑，对话式立项的主语，同步 LLM 调用
> - **DAG 内 4 Agent**（5.1-5.4，原 1-4）：Collector / Analyst / Writer / QA，通过 LangGraph 编排，State 驱动 + 反馈闭环

### Agent 5.0: 立项 Agent (`ScopingAgent`)（v1.4 新增）

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

**`known_competitors` 来源说明**（v1.5 修订）：
- **首次调用**（从 `/tasks/new` 提交）：始终为空数组 `[]`——v1.5 起 `/tasks/new` 不再提供独立的竞品 chip 输入区，已知竞品名由 ScopingAgent 自己从 `user_brief` 中提取
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
    clarifying_questions: list[ClarifyingQuestion]
    rationale: str                                        # AI 拆解依据，留 trace + 可选展示
```

**对下游的承诺**：
- `competitors` 长度 ∈ [3, 5]——少于 3 时 ScopingAgent 必须用 AI 推荐补齐
- `dimensions` 中 `layer="core"` 的恰好 4 项（功能树 / 定价 / 画像 / SWOT），不可缺失，可改名
- `dimensions` 中 `source="ai_suggested"` 的条目 ≤ 4——`source="user_added"` 不计入此上限
- 输出**幂等**——同样的输入两次调用应给出**结构相同**（顺序可不同）的草案，方便用户多次「重新生成」时不大幅震荡

### Agent 5.1: 采集 Agent (`CollectorAgent`)

**使用模型**：`gemini-2.5-flash`（1M 上下文塞检索结果不慌；tool use 稳定；详见 §五.X 选型决策）

**职责**: 把"产品/竞品名"变成结构化原始数据

**工具集**:
- `web_search(query, max_results=5)` — v1.7 升级为 **HybridSearch Provider 模式**，对 CollectorAgent 透明（仍一句调用，拿到 `list[SourceCitation]`）；内部实现：
  - `SearchProvider` Protocol 抽象：`TavilyProvider`（主）→ `SerpApiProvider`（备）
  - **降级策略**：Tavily 失败（429 / timeout / 500 / 空结果）→ 自动切换 SerpApi，每次降级写入 `trace_log`（`stage="search.fallback"`）
  - **全失败**：抛 `SearchUnavailableError`，LangGraph CollectorAgent 节点走 retry（最多 3 次）
  - **启动时探测**：按 `TAVILY_API_KEY` / `SERPAPI_API_KEY` 可用性自动构建 provider 顺序；无任何 key 时明确报错
  - 返回的每条 `SourceCitation` 含 `provider` 字段（记录实际使用的 provider 实现名）
  - 代码路径：`backend/services/search/`（`providers/base.py` / `providers/tavily.py` / `providers/serpapi.py` / `hybrid.py`）
- `fetch_page(url)` — Playwright 抓取
- `app_review_fetch(app_name)` — 应用商店评论（可选）
- `SurveyTool(competitor, dimension_intent, collected_sources)` — v1.6 新增，问卷调研子工作流，四层级联：
  1. **Stage 1**：AI 设计问卷（`questionnaire_designer`，5-10 道题）
  2. **Stage 2**：检索公开调研数据（`existing_survey_finder`）+ 复用已采集用户评论（`user_voice_collector`）
  3. **Stage 3**：推断目标画像（`persona_inferrer`）→ `SurveyDistributor.distribute()` → 回收答卷（MVP 用 `SimulatedDistributor`，LLM 模拟作答，**显式标注 `ai_simulated`**）
  4. **Stage 4**：洞察归纳（`insight_aggregator`），强制溯源，产出 `SurveyResult`
  
  每个 Stage 出口写入 `trace_log`（命名约定见 §六 WorkflowState 注）；合规抓取走主线 `fetch_page` 策略，robots 拒绝域名进 `skipped_urls`。

**输入 Schema**（v1.1 修订）:
```json
{
  "scope_contract": "TaskScopeContract"  // 完整传入，Collector 自己从中派生 dimensions_required
}
```

**v1.1 行为变化**：
- 不再接收硬编码的 `dimensions_required: ["features", "pricing", ...]`
- 从 `scope_contract.dimensions` 派生采集计划：核心层维度 → 跑预设搜索模板；扩展层维度 → 用 `dimension.intent` 做 query 改写（例："重点看会员体系" → 搜索 `<竞品名> 会员体系 黑卡` `<竞品名> 折扣节奏`）
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

**v1.1 核心动作（按维度路由）**:

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

**输出 Schema**:
- `StructuredCompetitorProfile`（核心层产物，详见 §七 7.4）
- `list[ExtensionFinding]`（扩展层产物，详见 §七 7.7）
- `CrossCompetitorAnalysis`（多竞品对比，详见 §七 7.5）

### Agent 5.3: 撰写 Agent (`WriterAgent`)

**使用模型**：`deepseek-v4-pro`（中文长报告自然度 88，384K 输出容量写完 10-15 页不截断；与 AnalystAgent 同模型简化 prompt 风格协调；详见 §五.X 选型决策）

**职责**: 把结构化 Profile + 扩展产物写成给人看的报告

**v1.1 渲染规则**：
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

**关键约束**: 不允许产生不带引用的结论（强制引用机制，抑制幻觉），核心层和扩展层一视同仁

### Agent 5.4: 质检 Agent (`QAAgent`)

**使用模型**：`gpt-4o-mini`（JSON 结构化检查任务简单，便宜款够用；与跨家协调最少；详见 §五.X 选型决策）

**职责**: 触发反馈闭环

**v1.1 检查清单（分层判断）**:

| 检查项 | 核心层（`layer="core"`） | 扩展层（`layer="extension"`） |
|---|---|---|
| Schema 完整性 | 必填字段缺失 → **blocker** | 字段稀疏（无 bullets/table_data）→ warning |
| 引用强制 | `source_ids` 缺失 → **blocker** | `source_ids` 缺失 → **blocker**（扩展层也强制溯源） |
| 事实校验 | 抽样 LLM 校验，矛盾 → blocker | 抽样 LLM 校验，矛盾 → warning |
| 数据新鲜度 | 信源 > 2 年 → warning | 信源 > 2 年 → warning |
| 覆盖度 | 每个竞品 ≥ 5 独立信源 → 否则 blocker | 每个维度 ≥ 1 信源 → 否则 warning |

**v1.6 新增：SurveyInsight 专项校验**（仅在 `WorkflowState.survey_results` 存在时触发）：

| 检查项 | 级别 | 说明 |
|---|---|---|
| `SurveyInsight.evidence_ids` 非空 | **blocker** | 每条洞察必须关联至少 1 条 `SurveyEvidence`，不可为空列表 |
| 每条 `SurveyInsight` 含 ≥1 条真实来源 | **blocker** | `evidence_ids` 指向的 evidence 中，`source_type` 为 `published_survey` 或 `public_review` 的条数 ≥ 1；不允许一条洞察 100% 由 `ai_simulated` 支撑 |
| `SurveyResult.source_breakdown["ai_simulated"] / total` ≤ 60% | **warning** | 整个 SurveyResult 的模拟占比过高时写入 trace 并在报告页"数据构成"区显示黄色警示；不阻塞流程 |
| `representative_quotes` 含 `ai_simulated` 时前端强制显示 ⚠️ | **约定**（非阻塞） | QAAgent 输出 issue 标记（`severity: "convention"`），前端渲染必须消费此标记；若前端未渲染则视为前端 bug |

**反馈闭环逻辑**：
- **blocker** → 打回 Collector 重抓（最多 3 次），3 次仍失败则字段标"未确认"
- **warning** → 不阻塞流程，在最终报告中标"未充分确认"提示

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
    scope_contract: TaskScopeContract                     # v1.1 新增，对话式立项产物
    raw_collections: dict[str, RawCollectionResult]       # competitor → result
    structured_profiles: dict[str, StructuredCompetitorProfile]  # 核心层产物
    extension_findings: list[ExtensionFinding]            # v1.1 新增，扩展层产物
    survey_results: dict[str, SurveyResult] | None        # v1.6 新增，competitor → SurveyResult
    cross_analysis: CrossCompetitorAnalysis | None
    draft_report: ReportDraft | None
    qa_result: QAResult | None
    retry_counts: dict[str, int]                          # node_name → count
    trace_log: list[TraceEntry]                           # 完整决策日志
```

`scope_contract` 在进入 DAG 时已 `frozen`，下游所有 Agent **只读**；保证一次任务的"维度规格"不可在跑批中途漂移。

**v1.6 SurveyTool trace 命名约定**：SurveyTool 每个 Stage 出口必须写入一条 `TraceEntry`，`stage` 字段命名如下：

| Stage | trace stage 值 |
|---|---|
| Stage 1 问卷设计 | `survey.stage1.designer` |
| Stage 2a 公开调研检索 | `survey.stage2a.existing` |
| Stage 2b 用户声音收集 | `survey.stage2b.voice` |
| Stage 3a 目标画像推断 | `survey.stage3a.persona` |
| Stage 3b 问卷分发 | `survey.stage3b.distribute` |
| Stage 3c 答卷回收 | `survey.stage3c.collect` |
| Stage 4 洞察归纳 | `survey.stage4.aggregate` |

**v1.7 新增：HybridSearch trace 命名约定**：

| 事件 | trace stage 值 | 必含字段 |
|---|---|---|
| 主搜索调用 | `search.invoke` | `provider`（使用的 provider 名）、`query`、`results_count` |
| Provider 降级 | `search.fallback` | `failed_provider`、`failure_reason`、`next_provider` |
| 全部 provider 失败 | `search.exhausted` | `tried_providers`、`final_error` |

每条 trace entry 需包含：`prompt_hash`、`input_summary`、`output_summary`、`latency_ms`、`tokens_in`、`tokens_out`、`failure_reason`（nullable）、`provider_impl`（Stage 3 Survey 专用，值为 Distributor 实现类名）。

**禁止**：Agent 之间用自然语言对话传消息。所有交互必须通过 State 字段（满足评分项"结构化消息传递 / function calling"）。

---

## 七、竞品知识 Schema 设计

> **v1.1 架构**：Schema 分**两层**——
> - **核心层（固定）**：7.1 FeatureTree / 7.2 PricingModel / 7.3 UserPersona / 7.4 SWOT。**所有任务都必须产出**，是比赛"严格符合预定义 Schema"评分项的承诺对象。
> - **扩展层（动态）**：7.7 ExtensionFinding。由对话式立项阶段 AI 与用户协商生成（见 §四 [3] 与 7.0 TaskScopeContract），**每个任务的扩展维度不一样**，是"按场景定制"的承诺对象。
>
> QA Agent 对两层做差异化校验：核心层缺失字段 = blocker（硬打回 Collector）；扩展层缺失 = warning（标记"未确认"，不阻塞）。详见 §六 QA Agent 与 §十三 验收标准。

### 7.0 任务范围契约 (`TaskScopeContract`)

**v1.1 新增**。对话式立项阶段的最终产出，是 §四 [3] 到 [4] 的交接物，也是后续 4 个 Agent 的"任务规格书"——所有 Agent 决定"做什么 / 抽什么 / 写什么 / 校验什么"都从这里读。

```python
class DimensionSpec(BaseModel):
    id: str                          # "core.feature_tree" / "ext.channel_structure" / "ext.<slug>"
    layer: Literal["core", "extension"]
    source: Literal["system", "ai_suggested", "user_added"]  # v1.5: 区分来源，决定上限规则
    title: str                       # 用户可改的章节标题：「会员体系与折扣节奏」
    intent: str                      # 用户可改的"意图描述"，喂给 Analyst prompt 做指向性约束
    schema_ref: str | None           # 核心层指向固定 Schema（"FeatureTree" / "PricingModel" 等）；扩展层为 None
    enabled: bool                    # 用户勾选开关（核心层强制 True，UI 上 checkbox 置灰）
    locked: bool                     # 核心层为 True，UI 上禁用删除按钮
    order: int                       # 章节顺序（用户可拖拽调整，核心和扩展可混排）

class TaskScopeContract(BaseModel):
    task_id: str
    target_product: str | None       # 可选——用户描述的"我家产品"
    competitors: list[str]           # 用户确认的竞品名（NL 提取 + chip 合并去重）
    user_brief: str                  # 用户最初的 NL 描述（原文留存，供回溯）
    clarifications: list[dict]       # AI 提的澄清问题 + 用户答案（可为空，用户可全部跳过）
    dimensions: list[DimensionSpec]  # 大纲：核心 4 项 + N 项扩展，按 order 排好
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
  "type": "url | document | published_survey | public_review | ai_simulated",
  "url": "string",
  "title": "string",
  "snippet": "string",  // 原文片段
  "agent": "CollectorAgent",
  "provider": "string | null",  // v1.7 新增：产出该引用的 SearchProvider 实现名（"tavily" / "serpapi" / null）
  "fetched_at": "ISO8601"
}
```

**v1.6 type 枚举变更**：
- `url` — 普通网页抓取（web_search / fetch_page）
- `document` — 上传文档（本期不实现，枚举占位）
- `published_survey` — 公开调研报告 / 行业数字（SurveyTool Stage 2a）
- `public_review` — 公开评论 / 社媒帖子（SurveyTool Stage 2b）
- `ai_simulated` — LLM 模拟答卷（SurveyTool Stage 3，**必须显示 ⚠️ AI 生成标记**）
- ~~`simulated_survey`~~ → 废弃，统一用 `ai_simulated`（如有历史数据迁移到 `ai_simulated`）

所有报告字段中的 `source_ids: ["src_001", ...]` 都指向 `SourceCitation`，前端渲染时变成可点击图标。`ai_simulated` 类型在前端渲染时**强制**显示灰色 badge + 🤖 图标 + ⚠️ 警示标，不可省略。

### 7.7 扩展维度产出 (`ExtensionFinding`)（扩展层）

**v1.1 新增**。承接对话式立项阶段动态生成的扩展维度。每个扩展维度 × 每个竞品产出一条 `ExtensionFinding`。

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

### 7.8 Survey 系列 Schema（v1.6 新增）

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
        "published_survey",                        # Stage 2a：公开调研报告 / 行业数字
        "public_review",                           # Stage 2b：公开评论 / 社媒
        "ai_simulated",                            # Stage 3：LLM 模拟答卷（⚠️ 必须标注）
    ]
    source_id: str                                 # 指向 §7.6 SourceCitation
    raw_quote: str                                 # 原文片段 / 模拟回答文本
    persona_inferred: str | None                   # LLM 推断的画像标签

class SurveyInsight(BaseModel):
    question_id: str
    point: str                                     # "黑卡门槛过高"
    frequency: int                                 # 在 evidence 里出现次数
    representative_quotes: list[str]               # 代表性原话 2-3 句
    evidence_ids: list[str]                        # 强制溯源，非空（QAAgent blocker）
    confidence: Literal["high", "medium", "low"]  # 按 source_type 构成自动推断

# confidence 推断规则：
#   real_ratio = (published_survey + public_review 数) / total evidence 数
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

---

## 八、API 划分

### 8.1 认证
- `POST /api/auth/send-code` — 发邮箱验证码
- `POST /api/auth/verify` — 验证码登录，返回 JWT
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
- `POST /api/tasks/{id}/retry-node` — 用户手动触发某节点重跑

### 8.4 报告
- `GET /api/reports/{task_id}` — 网页渲染数据（结构化 JSON）
- `GET /api/reports/{task_id}/export?format=pdf|pptx|markdown` — 导出
- `PATCH /api/reports/{task_id}/field` — 人工修正某字段（触发局部重跑）

### 8.5 竞品推荐（B 入口）
- `POST /api/competitors/suggest` — 输入产品+赛道描述，返回竞品候选

---

## 九、前端线框图（文字描述）

### 页面 1a: 任务创建页 `/tasks/new`（v1.3）
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
> **v1.5 简化**：页面只有 NL 单输入 + 示例 chips + 主操作按钮。竞品名 chip 输入区已移除（已知竞品由 ScopingAgent 从 NL 提取，立项页才允许增删）。「30 秒演示」入口已迁至全站顶部导航栏。
>
> **按钮文案双态**：当 NL 含「直接生成 / 跳过 / 不要大纲 / directly / skip / no plan」等关键词时，按钮文案切换为「直接分析 →」，提交后跳过 scoping 页直接进入分析（演示路径 `/demo/scoping`）。否则默认「生成研究计划」走 ScopingAgent。

### 页面 1b: 对话式立项 / scoping 页 `/tasks/new/scoping`（v1.1 新增）
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
┌─────────────────────────────────────────┐
│  [产品A vs 产品B vs 产品C]               │
│  [导出PDF] [导出PPTX] [回放DAG]          │
├─────────────────────────────────────────┤
│ § 摘要                                   │
│ 三款产品在...有显著差异 [src①②]         │
│                                         │
│ § 功能对比矩阵                           │
│ ┌────────┬────┬────┬────┐               │
│ │ 功能   │ A  │ B  │ C  │               │
│ ├────────┼────┼────┼────┤               │
│ │ 用户管理│ ✓ │ △ [src] │ ✗ │           │
│ └────────┴────┴────┴────┘               │
│                                         │
│ § SWOT（每个竞品一张）                  │
│ § 定价对比                              │
│ § 用户画像                              │
│                                         │
│ [点击任意 src 图标 → 右侧弹溯源面板]    │
└─────────────────────────────────────────┘
```

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
  id uuid PK, task_id FK,
  status text, retry_count int,
  langgraph_thread_id text,                -- LangGraph checkpointer 用
  started_at, completed_at
)

-- Trace 日志（每个 Agent 节点一条）
agent_traces (
  id uuid PK, task_run_id FK,
  agent_name text, node_name text,
  prompt text, input_payload jsonb, output_payload jsonb,
  tokens_used int, latency_ms int,
  decision_meta jsonb,                     -- 决策摘要（为何打回等）
  created_at
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
  version int,
  qa_status text,                          -- passed/issues
  qa_issues jsonb,
  created_at
)

-- 人工修正历史（P1）
manual_corrections (
  id uuid PK, report_id FK,
  field_path text, old_value jsonb, new_value jsonb,
  triggered_rerun boolean, user_id FK, created_at
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

### P1 (第二期/加分项)

- 人工介入修正字段 + 触发局部重跑
- Agent 决策时间轴回放
- 历史报告语义检索（RAG 复用素材）
- 应用商店评论真实抓取（目前用 LLM 模拟也可）
- 多语言报告（中/英切换）

### P2 (远期，PRD 仅占位)

- 全自动竞品发现（仅赛道关键词输入）
- 自适应任务拆分（Agent 自决定要不要拆子任务）
- Agent 自评估 + 动态 Schema 演化
- 多人协作编辑同一报告

---

## 十一-bis、Non-Goals（v1.2 新增，本次比赛 MVP 显式不做的事）

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
- ❌ 真实用户并发压测（演示日靠 Railway 临时升档 + 预置账号兜底，见 §十二 风险表 v1.2 补充）

### 数据与合规层面（MVP 外）
- ❌ GDPR / 数据出域审计 / 数据脱敏管线
- ❌ 内部数据上传（如 §十四 G 提到的"上传公司销售数据"）—— 留给 P2
- ❌ **调用 embedding API**（MVP 不走 RAG；pgvector schema 字段保留 NULL，为 P1 "历史报告语义检索复用"准备，见 §十一-ter 设计钩子 2）
- ℹ️ ~~国内合规 LLM 替换~~ —— v1.8 起 MVP 已部分国产化（AnalystAgent + WriterAgent 用 DeepSeek V4 Pro，见 §五.X）；生产化阶段补充更多国产 Provider，见 §十一-ter 第二阶段

### 仍然要做的（提醒）
- ✅ **单任务内多 Agent 并行**（LangGraph `Send` API 做 fan-out，4 个竞品的采集并行而非串行）
  —— 这不是"高并发"，是单任务内的并行度优化，**直接影响演示节奏**
- ✅ **演示日运维预案**：Railway 临时升档 + 预置 3 个评委账号 + 完整的**演示模式（Demo Mode）静态回放路径**（详见 §十一-quater）

---

## 十一-ter、未来生产化路径（v1.2 新增，答辩用 / 路演用）

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
3. **TaskScopeContract（v1.1 新增）** —— Agent 的"做什么"与"怎么做"已解耦，
   未来加新行业模板不用改 Agent 代码
4. **所有 Agent 间通信走 Pydantic State，无自然语言对话** —— 未来替换 LLM 供应商
   （OpenAI → 智谱）只需改 prompt 模板，State Schema 不动
5. **Schema 双层架构（核心层固定 + 扩展层动态）** —— 未来 SaaS 化按行业卖
   "扩展模板包"有现成的扩展点

### Provider 模式统一架构（v1.6 新增，v1.7 扩充，**答辩叙事重点**）

> 本节说明 SurveyTool、HybridSearch、企业 KB 接入在架构上的统一设计思路。
> **MVP 已实现的 Provider 抽象**（2 个实证）：
> - `SearchProvider`（v1.7 升级）— 代码在 `backend/services/search/providers/`
> - `SurveyDistributor`（v1.6 引入）— 代码在 `backend/services/survey/distributors/`
>
> **生产化路线图占位**（本期 0 代码）：
> - `KnowledgeBaseProvider`

**核心思路**：所有外部数据采集能力都收敛为可插拔的 Provider，CollectorAgent 只与抽象接口通信，不感知底层实现；失败时按策略降级，全过程进 `trace_log`。

```
CollectorAgent
  ├── web_search()            → SearchProvider（Protocol）           [v1.7 升级]
  │     ├── TavilyProvider          ← 主，AI 优化的搜索
  │     └── SerpApiProvider         ← 备，Google 搜索 fallback
  │         降级策略：Tavily 429/超时 → 自动切 SerpApi
  │         全失败：抛 SearchUnavailableError → LangGraph 节点 retry
  │
  ├── fetch_page()            → (内置，Playwright；非 Provider)
  ├── app_review_fetch()      → (内置；非 Provider)
  │
  ├── SurveyTool              → SurveyDistributor（Protocol）         [v1.6]
  │     └── SimulatedDistributor  ← MVP 唯一实现（LLM 模拟）
  │         未来可替换为:
  │         TypeformDistributor / WenjuanxingProvider / 企业样本池
  │
  └── KnowledgeBaseProvider   ← 生产化占位（本期不实现）              [路线图]
        未来可实现:
        ConfluenceProvider / SharePointProvider /
        NielsenProvider / GleanProvider / SQLProvider
```

**`SearchProvider` Protocol（v1.7 MVP 已实现）**：

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

**`SurveyDistributor` Protocol（v1.6 MVP 已实现）**：

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

## 十一-quater、演示模式 / Demo Mode（v1.3 新增）

> **目的**：演示日 OpenAI / Tavily / Neon / Railway 任一抽风时，评委仍能完整体验产品全流程；同时降低评委试用的 token 成本（每次点击 = 0 美元）。
>
> **设计原则**：**纯前端静态回放，零后端调用**。与真实 LangGraph 流程并存、互不干扰。

### 11Q.1 入口（v1.5 更新）

demo 现在有**两个入口**，都不藏：

1. **全站顶部导航栏 `[▶ 30 秒demo演示]`**——任何页面都能一键直跳 `/demo/scoping`
2. **`/tasks/new` NL 关键词触发**——用户在 NL 中写「直接生成 / 跳过 / 不要大纲 / directly / skip / no plan」等，按钮自动切换为「直接分析」，提交后跳 `/demo/scoping`（MVP 阶段；后端就绪后接真实直跑路径）

> **v1.4 → v1.5 调整**：原"`/tasks/new` 页内并排两按钮"被拆开——「30 秒演示」上移到全站导航栏（任何页面可达），任务创建页只保留聚焦的 NL 输入 + 单一主按钮。
>
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

### 11Q.7 路由职责边界 / Route Isolation Contract（v1.5.1 新增，🔴 强约束）

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

### Week 0.5 (0.5 周): 架构落地与脚手架
- [ ] **创建项目入口文档**：`CLAUDE.md` + `AGENTS.md`（指引所有编程 Agent 读取 PRD、架构图、Agent 协议、Schema 文档）
- [ ] Repo 初始化（monorepo: `frontend/` + `backend/`）
- [ ] Railway 项目搭建 + Neon + Upstash 接入
- [ ] FastAPI + LangGraph 骨架，跑通 Hello World DAG
- [ ] Next.js + shadcn/ui 骨架，跑通登录页 UI
- [ ] 数据库 Schema 落库（Alembic 迁移）
- [ ] 关键 Pydantic Schema 定义（章节七的 Schema 转代码）

### Week 1 (1 周): Agent 单体开发
- [ ] CollectorAgent：搜索 + 网页抓取 + 输出 RawCollectionResult
- [ ] AnalystAgent：原始数据 → StructuredProfile
- [ ] WriterAgent：StructuredProfile → ReportDraft（带引用）
- [ ] QAAgent：检查 + 输出 issues
- [ ] 每个 Agent 单元测试（mock LLM）
- [ ] LangGraph DAG 串起来（无反馈闭环版本）

### Week 2 (1 周): 联调 + 反馈闭环 + 前端联动
- [ ] 反馈闭环逻辑（QA → 打回 → 重跑 → 改善验证）
- [ ] SSE 实时推送 DAG 状态
- [ ] 前端 DAG 可视化（用 React Flow 或 D3）
- [ ] 报告页交互（溯源面板、字段展开）
- [ ] PDF 导出（用 WeasyPrint 或 Playwright print）
- [ ] PPTX 导出（用 python-pptx）
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
| 3 周时间紧 | 功能砍不动 | P0 锁死，P1 按时间允许加，P2 不做 |
| 演示日多评委同时点 | 单实例 FastAPI 卡 SSE 长连接 | 临时把 Railway 从 Hobby 升到 Pro（workers 调到 8-16）+ 预置 3 个评委账号 + `/reports/demo` 不登录直接看的样例报告（v1.2 补充，对应 §十一-bis 演示日运维预案）|

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

> **v1.1 评分项备 answer**：评委可能问"扩展层是不是绕过了'预定义 Schema'要求"——回答：核心层 4 套 Schema 就是预定义对象，QA 对核心层缺失字段硬打回（演示时可触发）；扩展层是评分卡 25% 项里明文提到的"动态 Schema 演化"加分项的具体实现，与"严格符合预定义 Schema"不冲突。
>
> **v1.5 追问备 answer**：若评委进一步问"扩展层会不会被 AI 无限发散、失去 Schema 严肃性"——回答：扩展层有**双层数量约束**——ScopingAgent 单次最多建议 **4 个**（`source="ai_suggested"`，写进 TaskScopeContract 不变式 + prompt 双重保险），保证 AI 自主性可控；用户手动添加的扩展维度（`source="user_added"`）不设上限，把"模型保守 + 人类自由"显式分离，正是 35% 评分卡里"Agent 间通信协议清晰"和 20% "人工介入修正易用直观"两项的具体落地。

### 技术深度与工程完整度 (25%)
- ✅ 端到端可访问：登录 → 创建 → **对话式立项** → 跑 → 看报告 → 导出，全链路无中断
- ✅ 每个 Agent 的 Prompt / 输入 / 输出 / Token / 延迟 在 Trace 页可查
- ✅ 幻觉抑制策略明确：强制引用 + QA 事实校验 + 多源交叉
- ✅ 异常处理：网络失败重试、API 限流降级、节点失败标记并继续
- ✅ **动态 Schema 演化**已落地（v1.1 主张，非仅口头）：TaskScopeContract + 双层 Schema，可演示同一套代码跑日化 / SaaS / 工业品三类截然不同的报告
- ✅ **自适应任务拆分**已落地：Collector 按 `dimension.intent` 做 query 改写，Analyst 按 `layer` 走差异化抽取器
- ✅ 前瞻性：pgvector 已接入，为 P1 的语义检索复用铺路

### 业务价值与产品体验 (20%)
- ✅ 5-10 分钟出报告 vs 人工 1-2 天（演示时计时对比）—— 注意：对话式立项阶段计入"分析时间"还是分开报告？演讲时建议分开，因为这是用户感知的"主动配置"时间，不算等待
- ✅ 自动覆盖 ≥5 信息源（数量统计在报告底部展示）
- ✅ **Schema 按场景动态生成**（演示换行业不用改代码，演示同时跑日化 + SaaS 对比说明性最强）
- ✅ 关键指标：完整率（核心层）、信源数、QA 通过率 在报告页可见
- ✅ 交互流畅：溯源、导出、回放主路径 ≤3 次点击
- ✅ **入口体验贴合真实工作流**（v1.1 价值主张）：用户用自然语言描述需求，AI 协商出本次任务的维度大纲，对比"勾选预设维度"的填表式入口，更接近"和分析师同事讨论"的真实交互

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

---

## 十四、待办与未决问题

### 14.1 需要与战略部访谈（业务侧，他能回答）

**访谈目标**：用真实场景校准产品定位、Schema 字段、报告形态，避免我们凭空设计。

**A. 工作流与场景**（核心问题，必问）
- [ ] 你接到一个竞品分析需求时，第一步通常做什么？典型耗时？
- [ ] 一次完整的竞品分析从立项到交付平均花多久？瓶颈在哪一步？
- [ ] 竞品列表是怎么来的——老板指定 / 自己调研 / 已知行业格局？
- [ ] 一次分析通常对比多少个竞品？（2-3 个还是 5-10 个）
- [ ] 这份分析最终交付给谁？（直属上级 / 跨部门 / 管理层）

**B. 字段与维度**（v1.1 修订：双层 Schema 验证）
- [ ] **核心层确认**：把我们的核心 4 类 Schema（功能树 / 定价 / 用户画像 / SWOT）给他看，问：
  - 这 4 项作为"所有任务都必出"的默认维度合不合理？
  - 在他工作流中，会不会出现"连功能树都不需要、SWOT 不重要"的任务？（如果有，说明核心层选 4 个选错了，要调整）
  - 用户画像的颗粒度——他需要的是"中产白领"这种标签，还是"30-40岁、一二线城市、有娃家庭"这种结构化描述？
- [ ] **扩展层 brainstorm 验证**（v1.1 新增）：演示对话式立项页面 / 拿截图给他看——
  - 让他用 NL 描述一个真实任务，看 AI 生成的扩展维度大纲，他会增删什么？
  - 收集 5-10 份真实任务的大纲，看哪些扩展维度**高频出现**（如日化场景的"渠道结构 / KOL / 促销节奏 / 线下铺货"）—— 这些可以作为"AI 默认推荐"的二级模板，下次同类任务自动出
  - 哪些维度他认为"AI 想都想不到、必须我自己加"？这些是产品边界
- [ ] **核心层「必填字段」清单**：从 §七 7.1-7.4 的每个 Schema 中圈出 3-5 个"必须填、宁可空着写'未确认'也不能没有"的字段。
  > 这直接决定 QA Agent 对**核心层**的"必填字段"清单（blocker 触发条件）。**扩展层不走必填判断**，缺失只标 warning。

**C. 信息源**（决定采集 Agent 的真实价值，必问）
- [ ] 他平时从哪些渠道获取竞品情报？（电商平台评论 / 行业报告 / 公司官网 / 经销商 / 内部数据）
- [ ] 公司有订阅的付费数据库吗？（如尼尔森、欧睿、Mintel）—— 这决定我们是否需要支持文档上传作为补充信源
- [ ] 哪些信源他认为最可信？哪些不可信？

**D. 报告交付物**（决定导出功能优先级，必问）
- [ ] 他平时交付的形态是什么——Excel 对比表 / Word 报告 / PPT 汇报？
- [ ] 如果只能选一种交付物，他选哪个？
- [ ] PPT 大概多少页？有内部固定模板吗？
- [ ] 报告中"结论可信度"他怎么标注的？（是否做过引用/溯源）

**E. 痛点与期望**（验证我们的价值主张，必问）
- [ ] 现在做竞品分析最痛苦的环节是什么？
- [ ] 如果有一个 AI 工具，他最想它先解决哪一件事？
- [ ] 他对 AI 生成的报告"信任度"如何？需要什么才能让他敢直接拿去汇报？
- [ ] **自动化边界**：他能接受哪种交付形态？
  - (a) AI 全自动产出报告，他**直接拿去汇报**
  - (b) AI 产出报告，他**逐节复核** / 修改后再用
  - (c) AI 只产出**素材包**（结构化数据 + 引用），他自己写结论
  - 不同字段是否有不同标准？（如"功能列表"可以全自动，"SWOT 结论"必须人工复核）
  > 这决定我们的"人工介入"功能是 P0（必须）还是 P1（加分）；也决定 Writer Agent 是写"完整结论"还是只写"候选结论"。

**F. 问卷调研与用户访谈**（决定采集 Agent 的"问卷"子能力如何设计，必问）

> 背景：题目明确提到"问卷设计、问卷调研、用户访谈"是采集 Agent 的职责。我们当前默认做"流程模拟"——Agent 生成问卷方案 + 模拟数据。但这是否贴合真实工作流，需要他来校准。

- [ ] 战略部做竞品分析时，**真的会做问卷调研吗**？还是主要靠桌面研究 + 现有数据？
- [ ] 如果会做问卷：
  - 谁来设计问卷？市场部 / 调研公司 / 战略部自己？
  - 一份典型问卷有多少题？覆盖哪些维度？（如品牌认知、购买意愿、使用频次、痛点、价格敏感度）
  - 问卷分发渠道是什么？（问卷星、专业调研公司、自有用户池、第三方样本库如尼尔森）
  - 一次问卷调研的平均周期和成本大概多少？
  - 拿到问卷数据后怎么用？（直接进报告？还是先做交叉分析？）
- [ ] 如果不亲自做问卷，**用户访谈/深访**是否做？谁做？什么频次？
- [ ] **关键判断题**：如果我们的 Agent 能做到以下哪一种，对他最有价值？
  - (a) **只生成问卷方案 + 维度建议**（他拿去给真实调研团队执行）
  - (b) 生成问卷 + 从公开渠道（电商评论/社媒）**抓取代理性反馈数据**当作"伪问卷结果"
  - (c) 生成问卷 + 让 **LLM 模拟不同画像的受访者**作答（明确标注"AI 模拟"）
  - (d) 这部分对他来说不重要，可以砍掉
- [ ] 他在公司里能拿到的真实"用户声音"数据是什么样的？（电商评论 / 客服记录 / NPS 问卷 / 经销商反馈）—— 这决定我们采集 Agent 是否应该支持上传内部数据作为信源

> 这组问题的产出将直接决定：CollectorAgent 中的 `generate_survey` 工具是做成 P0 重点能力，还是降级为 P1/P2 的"流程演示用"。

**G. 产品扩展性与边界**（决定 P1/P2 范围，建议问）

> 这组问题不阻塞 MVP，但答案能帮我们规划 P1/P2 优先级，避免做错方向。

- [ ] **数据时效性**：他做的竞品分析，结论"保鲜期"是多久？
  - 一周后还有效？还是当天就过期？
  - 是否需要"同一份报告每月自动复跑一次，看变化"？
  > 决定 P1 是否做"定期复跑 + 差异对比"功能。

- [ ] **可视化偏好**：除了我们现在设计的功能矩阵 + SWOT 文字，他汇报时通常会用到哪些图？
  - 市场份额饼图 / 价格散点图 / SKU 矩阵热力图 / 时间轴 / 渠道分布图…
  - 他是更习惯**静态图表插在 PPT 里**，还是**交互式 Dashboard 在大屏展示**？
  > 决定 Writer Agent 是否需要输出图表数据（如让前端用 ECharts 渲染）；PPTX 导出是否需要含图。

- [ ] **内部数据信源**（合规边界）：如果未来支持"上传公司内部数据"作为补充信源——
  - 哪些内部数据他**有权限**给 AI 系统看？（电商评论 / 客服记录 / 内部销售数据 / 经销商反馈）
  - 哪些**必须脱敏**或**绝对不能上传**？（财务、客户身份、内部战略文档）
  - 他公司对"数据出域到 OpenAI"这种事的态度是？
  > 决定 P2 是否做"上传内部数据"功能，以及是否需要替换成国内合规 LLM。

- [ ] **跨部门协作**：一份竞品分析报告，通常需要哪些部门一起看 / 用？
  - 产品 / 市场 / 运营 / 销售 / 高管？
  - 不同部门关心的字段是否不同？（如产品看功能，市场看定位与渠道）
  > 决定 P2 是否做"按角色定制报告视图"。但提醒：MVP 不做权限分层。

### 14.2 请战略提供的材料（如可能）

- [ ] **一份脱敏后的真实竞品分析报告**（PPT 或 Word）——用作我们 Schema 和报告排版的参照基准
- [ ] **汉高内部使用的竞品分析框架/模板**（如有）——可能藏着行业 know-how
- [ ] **常用付费数据库/工具清单**——判断是否要在 P2 支持外部数据导入
- [ ] **1-2 个具体竞品分析案例**（产品名+对比竞品）作为我们演示的备选案例

### 14.3 技术侧决策

- [ ] OpenAI API key 来源（个人 / 团队共享 / 走代理）
- [ ] Tavily vs SerpApi 选型（建议 Tavily，LLM 链路更顺）
- [ ] PPTX 模板设计（建议 Week 0.5 末做 POC 确认风格——可参考 14.2 拿到的真实模板）
- [ ] DAG 可视化库选型（React Flow vs Dagre+D3，建议 React Flow）
- [ ] 溯源面板的视觉规范（避免点击溯源后体验割裂）

### 14.4 访谈节奏建议

| 时间点 | 必问题组 | 选问题组 | 目标 |
|---|---|---|---|
| **访谈 1（Week 0 / 启动前）** | A + B + E | F | 校准 Schema 与价值主张；带 PRD §二 用户画像 + §七 Schema 草案 |
| **材料收集（Week 0.5 内）** | — | — | 拿到 §14.2 的脱敏报告与框架 |
| **访谈 2（Week 2 联调期）** | D | G | 拿初版 demo 试用，验证交付物形态、信任度、可视化偏好、未来扩展方向 |

**问题组保留状态说明**：A / B / C / D / E / F 为必问；G 为补充扩展性问题（不阻塞 MVP）。原始补充建议中"数据缺失如何处理（产品设计题）"和"分层权限展示（MVP 范围外）"已主动剔除。

---

## 十五、关键文件路径预告（交给开发 Agent）

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

---

## 验证（如何确认这个 PRD 可执行）

1. **PM 与项目负责人 walk-through**：本文档逐节确认，特别是 Schema 和 Agent 协议
2. **与汉高战略部实习生访谈**：用本 PRD 第二节 + 第七节 Schema 草案做引导，确认场景与字段
3. **开发 Agent 拆任务**：把本 PRD 喂给后续开发 Agent，要求其按 Week 0.5 / 1 / 2 / 0.5 节奏拆 issue 到 GitHub Project
4. **Week 0.5 末检查点**：脚手架跑通 = PRD 落地无障碍

---

**本 PRD 是开发 Agent 的输入。任何改动需要 PM 与项目负责人同意并更新本文档版本。**
