# PRD: AI 驱动的竞品分析 Agent 协作系统

> **文档性质**: 产品需求文档（PRD），交付给开发 Agent 拆任务用
> **版本**: v1.2
> **日期**: 2026-05-24
> **作者**: PM (Claude) + 项目负责人
>
> **v1.1 修订说明**（2026-05-23）：基于汉高战略部实习生反馈与比赛评分卡复核，引入**对话式立项 + 双层 Schema** 架构。固定 Schema（功能树/定价/画像/SWOT）保留为"核心层"满足比赛"严格符合预定义 Schema"评分项；新增"扩展层"由 AI 与用户协商动态生成，解决"维度因行业而异、无法预先穷尽"的真实痛点。详见本次修订设计草案 [plans/2026-05-23-dynamic-outline-scoping-design.md](../plans/2026-05-23-dynamic-outline-scoping-design.md)。影响章节：§四 / §六 / §七 / §九 / §十三 / §十四。
>
> **v1.2 修订说明**（2026-05-24）：显式声明 MVP 不做的事（避免开发 Agent over-engineering），并补一节"未来生产化路径"作为答辩材料。**不改动任何业务逻辑、Agent 设计或 Schema**，仅新增 §十一-bis Non-Goals、§十一-ter 未来生产化路径，§十二 风险表追加一行演示日并发兜底。详见 [plans/2026-05-24-prd-non-goals-and-future-scale.md](../plans/2026-05-24-prd-non-goals-and-future-scale.md)。

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
    主输入框：自然语言描述需求
      例：「分析 SK-II / 资生堂 / 雅诗兰黛，重点看会员体系与 KOL」
    可选 chip：手动追加竞品名（若 NL 中已含，AI 会自动提取并展示去重）
    点击「生成大纲」→
    ↓
[3] 对话式立项（scoping 页 /tasks/new/scoping）：
    AI 一次响应同时返回：
      (a) 初步大纲（核心 4 章 🔒 + N 项扩展章节 ✏️，每章带「意图描述」）
      (b) 1-3 个补充澄清问题（可跳过）
      (c) 从 NL 中识别到的竞品列表（用户可增删）
    用户编辑：
      - 核心章节（🔒 功能树 / 定价模型 / 用户画像 / SWOT）可改名 / 改意图 / 调顺序，不可删
      - 扩展章节（✏️ 任务相关维度）可改名 / 改意图 / 调顺序 / 删除 / 自定义新增
      - 「重新生成大纲」按钮 = 带当前编辑过的章节 + 澄清回答回到 AI 再生成
    用户点「确认 → 开始分析」时，大纲 freeze 成 TaskScopeContract（见 §七 7.0）
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

### Agent 3: 撰写 Agent (`WriterAgent`)

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

### Agent 4: 质检 Agent (`QAAgent`)

**职责**: 触发反馈闭环

**v1.1 检查清单（分层判断）**:

| 检查项 | 核心层（`layer="core"`） | 扩展层（`layer="extension"`） |
|---|---|---|
| Schema 完整性 | 必填字段缺失 → **blocker** | 字段稀疏（无 bullets/table_data）→ warning |
| 引用强制 | `source_ids` 缺失 → **blocker** | `source_ids` 缺失 → **blocker**（扩展层也强制溯源） |
| 事实校验 | 抽样 LLM 校验，矛盾 → blocker | 抽样 LLM 校验，矛盾 → warning |
| 数据新鲜度 | 信源 > 2 年 → warning | 信源 > 2 年 → warning |
| 覆盖度 | 每个竞品 ≥ 5 独立信源 → 否则 blocker | 每个维度 ≥ 1 信源 → 否则 warning |

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
    cross_analysis: CrossCompetitorAnalysis | None
    draft_report: ReportDraft | None
    qa_result: QAResult | None
    retry_counts: dict[str, int]                          # node_name → count
    trace_log: list[TraceEntry]                           # 完整决策日志
```

`scope_contract` 在进入 DAG 时已 `frozen`，下游所有 Agent **只读**；保证一次任务的"维度规格"不可在跑批中途漂移。

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
- 核心 4 项的 `enabled=True`、`locked=True`、`schema_ref` 不可为 None
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
  "type": "url | document | simulated_survey",
  "url": "string",
  "title": "string",
  "snippet": "string",  // 原文片段
  "agent": "CollectorAgent",
  "fetched_at": "ISO8601"
}
```

所有报告字段中的 `source_ids: ["src_001", ...]` 都指向 `SourceCitation`，前端渲染时变成可点击图标。

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

### 页面 1a: 任务创建页 `/tasks/new`（v1.1）
```
┌─────────────────────────────────────────────────────────┐
│ [Logo] AI 竞品分析                                 [我] │
├─────────────────────────────────────────────────────────┤
│ 创建分析任务                                            │
│                                                         │
│ 说说你的分析需求 *                                       │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 例：帮我对比 SK-II / 资生堂 / 雅诗兰黛 三个高端    │ │
│ │ 护肤品牌在中国电商会员体系和 KOL 策略上的差异     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 竞品名称（可选——不填会从上面 NL 自动提取）              │
│ [+ 输入名称后按 Enter]                                  │
│                                                         │
│                         [生成大纲 →]                    │
└─────────────────────────────────────────────────────────┘
```

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
- 🔒 标记 = 核心层（`layer="core"`），删除按钮置灰；[✎] 改名和意图始终开启
- ✏️ 标记 = 扩展层（`layer="extension"`），所有按钮可用
- 拖动手柄 ⇅ 调整 `dimensions[].order`，核心和扩展可混排
- 「重新生成大纲」= 带当前编辑过的章节 + 澄清回答回到 AI 再生成一版（不是完全推倒）
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
- ❌ 国内合规 LLM 替换（演示用 OpenAI；生产环境另说，见 §十一-ter）

### 仍然要做的（提醒）
- ✅ **单任务内多 Agent 并行**（LangGraph `Send` API 做 fan-out，4 个竞品的采集并行而非串行）
  —— 这不是"高并发"，是单任务内的并行度优化，**直接影响演示节奏**
- ✅ **演示日运维预案**：Railway 临时升档 + 预置 3 个评委账号 + `/reports/demo` 不登录可看的样例报告

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
| **合规** | OpenAI → 国内合规 LLM（智谱 / 阿里通义）双供应商 | 客户在国内必走 |

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
