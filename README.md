# AI 竞品分析 Agent 系统

> 字节跳动 AI 编程大赛参赛作品 · 3 周开发周期

多 Agent 协作的竞品分析系统。用户以自然语言描述需求，5 个专职 Agent 自动完成"采集 → 分析 → 撰写 → 质检"全流程，5-10 分钟内产出结构化竞品报告，支持 PDF / Markdown 导出格式。


本项目为个人参赛作品。GitHub Contributors 中出现的两个账号均为本人账号：
- `XuZiHan-010`：主要开发账号
- `xuzihan-002`：本人用于部署与环境测试的辅助账号
---

## 架构概览

```
用户 NL 输入
    ↓
ScopingAgent  — 对话式立项，生成 TaskScopeContract（竞品列表 + 分析大纲）
    ↓
CollectorAgent  — 多源采集（官网 / 搜索 / 应用商店 / 评论）
    ↓
AnalystAgent    — 结构化分析，写入 Schema（功能树 / 定价 / 画像 / SWOT + 扩展维度）
    ↓
QAAgent         — 质检，不通过则打回上游重做（反馈闭环）
    ↓
WriterAgent     — 生成报告草稿
    ↓
结构化报告（PDF / Markdown）
```

LangGraph 驱动 DAG，Agent 间通过 `WorkflowState` 结构化消息通信，前端实时显示进度。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 16 · React 19 · Tailwind v4 · Base UI |
| 后端 | FastAPI · LangGraph · Pydantic v2 |
| AI | DeepSeek (`deepseek-v4-pro`：Analyst / Writer) · OpenAI (`gpt-4o-mini`：Scoping / Collector / QA) · Tavily (搜索采集) · LangSmith (追踪) |
| 数据库 | Neon (PostgreSQL) · Upstash Redis (任务队列) |
| 部署 | Railway |

---

## 快速启动

### 前端

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

### 后端

```bash
cd backend
pip install -e .
uvicorn main:app --reload   # http://localhost:8000
```

### 环境变量

前端：复制根目录 `.env.example` 为 `frontend/.env.local`。
后端：复制 `backend/.env.example` 为 `backend/.env`，填入各平台 API key（DeepSeek / OpenAI / Tavily / Neon / Upstash / LangSmith）。

```bash
cp .env.example frontend/.env.local
cp backend/.env.example backend/.env
```

---

## 项目结构

```
competitor_analysis/
├── frontend/       Next.js 前端
├── backend/        FastAPI + LangGraph 后端（5 Agent · DAG · 导出）
├── docs/           项目文档
└── agent-states/   Agent 运行时状态（应用层）
```

---

## 文档

| 文档 | 说明 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | 完整产品需求文档（v1.4） |
| [docs/tech-stack.md](docs/tech-stack.md) | 技术选型与依赖说明 |
| [docs/git-workflow.md](docs/git-workflow.md) | 分支管理与提交规范 |
| [docs/ai-collaboration.md](docs/ai-collaboration.md) | AI 深度协作分工与证据链说明 |
| [claude-progress.txt](claude-progress.txt) | 开发进度日志 |

---

## 评分维度（比赛评分卡）

| 维度 | 权重 | 关键设计 |
|---|---|---|
| 多 Agent 协作 | 35% | LangGraph DAG · 反馈闭环 · Agent 间结构化消息 |
| 技术深度 | 25% | ScopingAgent 意图识别 · 双层 Schema · 实时 DAG 可视化 |
| 业务价值 | 20% | 5-10 min 出报告 · 可溯源结论 · PDF/Markdown 导出 |
| 代码质量 | 10% | Conventional Commits · lint 0 error · 模块化 |
| 规范遵从 | 10% | PRD 驱动开发 · Schema 严格对齐 |
