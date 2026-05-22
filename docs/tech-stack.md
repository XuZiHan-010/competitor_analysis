# 技术栈

> 本文档定义本项目的技术选型与每项选型的"为什么"。
> 任何 Agent 在写代码前，先在 [CLAUDE.md](../CLAUDE.md) 的索引中确认是否需要读本文件。

---

## 项目定位（一行）

AI 驱动的多 Agent 协作竞品分析系统。4 个专职 Agent（采集 / 分析 / 撰写 / 质检）通过 LangGraph 编排自动产出可溯源的结构化报告。最终部署到 Railway。

---

## 选型总表

| 层 | 选型 | 为什么 |
|---|---|---|
| 前端框架 | Next.js (App Router) + TypeScript | Railway 原生支持；SSR + RSC；shadcn 生态成熟 |
| 前端 UI | Tailwind CSS + shadcn/ui | 组件库质量高，适合仪表盘型产品 |
| 后端 | FastAPI (Python 3.11+) | 与 LangGraph 同语言；自动 OpenAPI；性能足够 |
| Agent 编排 | **LangGraph**（必选） | 比赛课题明确考察点；DAG 可视化 + Checkpointer + 反馈闭环都是一等公民 |
| LLM | OpenAI GPT-4o / GPT-4.1 | 生态成熟、function calling 稳定 |
| 搜索 API | Tavily（首选） / Serper（备选） | Tavily 专为 LLM 链路设计，返回结构化已清洗内容 |
| 网页抓取 | Playwright (Python) | 复杂页面（含 JS 渲染）可处理 |
| 数据库 | **Neon Postgres**（免费 3GB） + pgvector | LangGraph Checkpointer 官方支持 PG；pgvector 内置；3GB 比 Supabase 500MB / Atlas 512MB 更宽裕 |
| 缓存 / 队列 | **Upstash Redis**（免费） | 任务队列 + SSE 推送；免费额度 10K commands/天足够 demo |
| 实时通信 | Server-Sent Events (SSE) | 比 WebSocket 简单，单向推送 DAG 进度足够 |
| PDF 导出 | WeasyPrint 或 Playwright print | 二选一，看排版需求 |
| PPTX 导出 | python-pptx | Python 生态标准 |
| 认证 | 邮箱验证码 + JWT | 不引入 OAuth Provider 依赖 |

---

## 部署目标

| 服务 | 平台 | 计费 |
|---|---|---|
| Frontend (Next.js) | Railway | Hobby ~$3/月 |
| Backend (FastAPI) | Railway | Hobby ~$3-5/月 |
| Postgres + pgvector | Neon | Free Forever (3GB) |
| Redis | Upstash | Free (10K commands/天) |
| LLM | OpenAI API | 按用量计费（演示约 $20-50） |
| Search API | Tavily / Serper | 免费额度 |

---

## 不在选型范围内（明确排除）

- ❌ **CrewAI**：题目允许但已选 LangGraph，不混用
- ❌ **MongoDB**：LangGraph Checkpointer 在 PG 上是一等公民，Mongo 要自己写适配
- ❌ **Supabase Auth**：自建邮箱验证码逻辑简单，不引入额外服务依赖
- ❌ **Streamlit / Gradio**：评分项"交互设计"要求专业 SaaS 体验
