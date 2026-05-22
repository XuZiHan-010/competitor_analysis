# PRD: AI 驱动的竞品分析 Agent 协作系统

> **文档性质**: 产品需求文档（PRD），交付给开发 Agent 拆任务用
> **版本**: v1.0
> **日期**: 2026-05-21
> **作者**: PM (Claude) + 项目负责人

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
[2] 新建分析任务：
    选项 A：输入目标产品名 + 手动输入竞品列表
    选项 B：输入目标产品名 + 赛道描述 → 系统推荐竞品 → 用户勾选确认
    选项 C：仅输入赛道关键词 → 系统全自动发现竞品
    （MVP 默认 A+B，C 作为 P2 探索）
    ↓
[3] 选择/确认分析维度（基于默认 Schema 可勾选启用项）
    ↓
[4] 启动 Agent 协作：
    实时显示 DAG 进度（哪个 Agent 在跑、跑到哪一步、Trace 可点开）
    采集 Agent → 分析 Agent → 撰写 Agent → 质检 Agent
                                              ↓
                            （质检不通过，打回上游 Agent 重做）
    ↓
[5] 报告产出：
    网页交互式（默认）+ 可导出 PDF / PPTX
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
│  - Checkpointer→PG  │    │  - Tavily / Serper (搜索)   │
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
| LLM | OpenAI API | 按用量计费（演示约 $20-50） |
| Search API | Tavily Free / Serper Free | 免费额度 |

---

## 六、多 Agent 设计（核心）

### Agent 1: 采集 Agent (`CollectorAgent`)

**职责**: 把"产品/竞品名"变成结构化原始数据

**工具集**:
- `web_search(query)` — 调 Tavily/Serper
- `fetch_page(url)` — Playwright 抓取
- `app_review_fetch(app_name)` — 应用商店评论（可选）
- `generate_survey(competitor)` — LLM 生成模拟问卷调研方案 + 模拟数据

**输入 Schema**:
```json
{
  "target_product": "string",
  "competitors": ["string"],
  "dimensions_required": ["features", "pricing", "user_persona", "reviews"]
}
```

**输出 Schema** (`RawCollectionResult`):
```json
{
  "competitor": "string",
  "sources": [
    {
      "type": "official_site | search | app_store_review | simulated_survey",
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

### Agent 2: 分析 Agent (`AnalystAgent`)

**职责**: 把原始数据结构化为竞品知识 Schema

**核心动作**:
1. 从 `RawCollectionResult` 抽取功能列表 → 构建功能树
2. 抽取定价信息 → 构建定价模型
3. 从评论/产品描述抽取用户画像
4. 生成单竞品 SWOT
5. 多竞品交叉对比 → 功能对比矩阵

**输出 Schema** (`StructuredCompetitorProfile`，详见第七节)

### Agent 3: 撰写 Agent (`WriterAgent`)

**职责**: 把结构化 Profile 写成给人看的报告

**输出**:
- 网页结构（JSON，前端渲染用）
- Markdown 全文（用于 PDF/PPTX 导出）
- 每段文字带 `source_ids` 引用，前端渲染时变成可点击的溯源链接

**关键约束**: 不允许产生不带引用的结论（强制引用机制，抑制幻觉）

### Agent 4: 质检 Agent (`QAAgent`)

**职责**: 触发反馈闭环

**检查清单**:
1. **Schema 完整性**: 所有必填字段是否填了
2. **引用强制**: 每条结论是否有 `source_ids`
3. **事实校验**: 抽样取结论 vs 原始数据，用 LLM 判断是否一致
4. **数据新鲜度**: 信源时间是否 > 2 年前
5. **覆盖度**: 信源数量是否 ≥ 阈值（如每个竞品 ≥5 个独立信源）

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
    raw_collections: dict[str, RawCollectionResult]      # competitor → result
    structured_profiles: dict[str, StructuredCompetitorProfile]
    cross_analysis: CrossCompetitorAnalysis | None
    draft_report: ReportDraft | None
    qa_result: QAResult | None
    retry_counts: dict[str, int]                          # node_name → count
    trace_log: list[TraceEntry]                           # 完整决策日志
```

**禁止**：Agent 之间用自然语言对话传消息。所有交互必须通过 State 字段（满足评分项"结构化消息传递 / function calling"）。

---

## 七、竞品知识 Schema 设计

### 7.1 功能树 (`FeatureTree`)

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

### 7.2 定价模型 (`PricingModel`)

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

### 7.3 用户画像 (`UserPersona`)

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

### 7.4 完整竞品档案 (`StructuredCompetitorProfile`)

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
  "type": "url | document | simulated_survey",
  "url": "string",
  "title": "string",
  "snippet": "string",  // 原文片段
  "agent": "CollectorAgent",
  "fetched_at": "ISO8601"
}
```

所有报告字段中的 `source_ids: ["src_001", ...]` 都指向 `SourceCitation`，前端渲染时变成可点击图标。

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

### 页面 1: 任务创建页 `/tasks/new`
```
┌─────────────────────────────────────────┐
│ [Logo] AI 竞品分析                  [我] │
├─────────────────────────────────────────┤
│  ① 你的产品                             │
│  [输入框: 产品名称]                      │
│  [输入框: 产品简介 / 赛道关键词]         │
│                                         │
│  ② 竞品（选一种方式）                   │
│  ( ) 我自己输入: [+ 添加竞品]           │
│  (•) 让 AI 推荐: [推荐按钮] → 弹候选    │
│                                         │
│  ③ 分析维度（默认全选）                 │
│  [✓] 功能树  [✓] 定价  [✓] 用户画像     │
│  [✓] SWOT    [✓] 评论摘要               │
│                                         │
│            [ 开始分析 ]                 │
└─────────────────────────────────────────┘
```

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

## 十二、3 周迭代计划

### Week 0.5 (0.5 周): 架构落地与脚手架
- [ ] **创建项目入口文档**：`CLAUDE.md` + `AGENTS.md`（指引所有编程 Agent 读取 PRD、架构图、Agent 协议、Schema 文档）
- [ ] Repo 初始化（monorepo: `apps/web` + `apps/api`）
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
| Tavily/Serper 抓取失败 | 信源不足 | 准备 fallback 到 LLM 直接生成（带"模拟"标记）|
| PPTX 生成质量不达预期 | 汇报体验差 | 提前 1 周做 PPTX POC，确认排版可行 |
| LangGraph 学习曲线 | 进度延迟 | Week 0.5 集中跑通官方示例 + checkpointer |
| 3 周时间紧 | 功能砍不动 | P0 锁死，P1 按时间允许加，P2 不做 |

---

## 十三、验收标准（对应评分维度）

### 多 Agent 协作与输出可信度 (35%)
- ✅ 4 个 Agent 各司其职，职责无重叠（代码注释 + 文档说明）
- ✅ LangGraph DAG 可在前端可视化，所有节点状态可追溯
- ✅ Agent 间通过 Pydantic State 通信（无自然语言对话）
- ✅ 反馈闭环现场可触发：构造缺失数据 → QA 打回 → 重跑后字段完整
- ✅ 100% 输出符合 Schema，字段完整率 ≥95%
- ✅ 每条结论可一键溯源到原始 URL+片段

### 技术深度与工程完整度 (25%)
- ✅ 端到端可访问：登录 → 创建 → 跑 → 看报告 → 导出，全链路无中断
- ✅ 每个 Agent 的 Prompt / 输入 / 输出 / Token / 延迟 在 Trace 页可查
- ✅ 幻觉抑制策略明确：强制引用 + QA 事实校验 + 多源交叉
- ✅ 异常处理：网络失败重试、API 限流降级、节点失败标记并继续
- ✅ 前瞻性：pgvector 已接入，为 P1 的语义检索复用铺路

### 业务价值与产品体验 (20%)
- ✅ 5-10 分钟出报告 vs 人工 1-2 天（演示时计时对比）
- ✅ 自动覆盖 ≥5 信息源（数量统计在报告底部展示）
- ✅ Schema 可配置（演示换行业不用改代码）
- ✅ 关键指标：完整率、信源数、QA 通过率 在报告页可见
- ✅ 交互流畅：溯源、导出、回放主路径 ≤3 次点击

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

**B. 字段与维度**（验证我们的 Schema 设计，必问）
- [ ] 把我们的功能树 / 定价 / 用户画像 / SWOT 四类 Schema 给他看，问：
  - 哪几项是必须的？
  - 缺了哪些日化/消费品行业特有的维度？（如**渠道结构**、**SKU 矩阵**、**促销策略**、**线下铺货**、**KOL/代言**、**市场份额**、**新品上市节奏**）
  - 哪些字段他实际用不上？
- [ ] 用户画像的颗粒度——他需要的是"中产白领"这种标签，还是"30-40岁、一二线城市、有娃家庭"这种结构化描述？
- [ ] **"绝对不可遗漏"清单**：如果某一份报告中下列字段缺一项，他会直接判定报告"不可用"？请他从我们的 Schema 中圈出 3-5 个"必须填、宁可空着写'未确认'也不能没有"的字段。
  > 这直接决定 QA Agent 的"必填字段"清单——这些字段缺失会触发硬性打回，重跑 3 次仍失败才允许标"未确认"。

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
- [ ] Tavily vs Serper 选型（建议 Tavily，LLM 链路更顺）
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
├── apps/
│   ├── web/                          # Next.js
│   │   ├── app/(auth)/login/
│   │   ├── app/tasks/new/
│   │   ├── app/tasks/[id]/page.tsx   # 进行中 DAG 页
│   │   ├── app/reports/[id]/page.tsx
│   │   └── components/dag-viewer/
│   └── api/                          # FastAPI
│       ├── routers/auth.py
│       ├── routers/tasks.py
│       ├── routers/reports.py
│       ├── agents/
│       │   ├── collector.py
│       │   ├── analyst.py
│       │   ├── writer.py
│       │   └── qa.py
│       ├── graph/
│       │   ├── workflow.py           # LangGraph DAG 定义
│       │   └── state.py              # WorkflowState Pydantic
│       ├── schemas/
│       │   ├── feature_tree.py
│       │   ├── pricing.py
│       │   ├── persona.py
│       │   └── report.py
│       ├── services/
│       │   ├── search.py             # Tavily/Serper wrapper
│       │   ├── scraper.py            # Playwright
│       │   └── exporter.py           # PDF/PPTX
│       └── db/
│           ├── models.py             # SQLAlchemy
│           └── migrations/
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
