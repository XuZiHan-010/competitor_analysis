# AGENTS.md

> **本文件是所有 AI 编程 Agent 的统一入口**（Codex / Claude Code / Cursor / Aider / TRAE 等通用）。
> [CLAUDE.md](CLAUDE.md) 只是 `@AGENTS.md` 的指针，避免内容漂移。
> 内容分五部分：① 安全红线、② 项目快速入门、③ 文档索引、④ 比赛 10% 评分承诺、⑤ 工作规范。

---

## 🔴 一、安全红线

### 红线 1：包含 env 的文件绝对不可以上传到 GitHub 或外泄

**绝对禁止入库的文件**：
- `.env`
- `.env.local`、`.env.development`、`.env.production`
- 任何含 `secret` / `credentials` / `key` / `token` 字样的文件
- Railway / Neon / Upstash / OpenAI / Tavily 的 API key 或连接字符串

**绝对禁止外泄的渠道**：
- 不要贴到 Slack / 微信 / 邮件 / Issue / PR 描述
- 不要贴到 ChatGPT / Claude.ai / 其他在线 AI 工具
- 不要写到任何文档（包括本地 markdown）
- 不要出现在演示视频 / 截图中

**强制规则**：
1. 仓库初始化第一时间配 `.gitignore`，包含 `.env`、`.env.*`、`*.pem`、`*.key`、`secrets/`、`credentials/`
2. `.env.example` 可以入库，但只含 key 名称，**不含真实值**
3. commit 前必须 `git diff --cached` 检查一遍
4. **禁止 `git add .` 或 `git add -A`**，永远显式列出要加的文件
5. 所有密钥走环境变量，**代码里禁止任何形式的硬编码**

**如果密钥已泄露**：立即到对应平台轮换密钥 → 通知项目负责人 → 用 `git filter-repo` 清理历史。详见 [docs/security.md](docs/security.md)。

### 红线 2：所有 plan 文件创建在本地 [plans/](plans/) 目录

- AI Agent 生成的 plan / 方案 / 草稿 / 任务拆解 **统一放 `./plans/`**
- 不要写到 AI Agent 的全局目录（如 `~/.claude/plans/`、Codex workspace 外部目录）
- 不要散落在项目其他位置（如 `backend/plan.md`）
- 命名建议：`YYYY-MM-DD-<topic>.md`
- 详见 [plans/README.md](plans/README.md)

---

## 二、项目快速入门

### Monorepo 布局

```
competitor_analysis/
├── frontend/       Next.js 16 + React 19 + Tailwind v4 + shadcn/ui（前端，已脚手架）
├── backend/        FastAPI + LangGraph + Pydantic（后端，Week 0.5 待落地）
├── docs/           项目文档（PRD / 架构 / Schema / 部署等）
├── plans/          AI Agent plan 文件（gitignored）
├── agent-states/   被构建系统的运行时状态（应用层，非 Claude 记忆）
├── USER_PREFERENCES.md  项目负责人长期协作偏好
└── claude-progress.txt  项目开发进度日志
```

### 常用命令（前端 [frontend/](frontend/)，npm）

| 操作 | 命令 |
|---|---|
| 装依赖 | `npm install` |
| 起 dev server | `npm run dev` |
| 生产构建 | `npm run build` |
| Lint | `npm run lint` |

> 后端 [backend/](backend/) 待 Week 0.5 脚手架落地后补 `uvicorn`、`pytest`、`ruff`、`mypy` 命令。届时同步更新本节，**并在 `backend/` 下建一份 `CLAUDE.md`**（参考已有的 [frontend/CLAUDE.md](frontend/CLAUDE.md)），把测试 / lint 命令写死在子目录，避免改后端一个文件却跑整个项目的测试套件浪费 context。
>
> **每个子目录的详细命令与约束**：见对应目录的 CLAUDE.md（如 [frontend/CLAUDE.md](frontend/CLAUDE.md)）——本表只给入门概览。

---

## 三、文档索引

### 任何工作前必读

| 文档 | 说明 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | 完整产品需求文档 —— 唯一事实源 |
| [ai竞品分析要求.txt](ai竞品分析要求.txt) | 比赛官方课题与评分标准 |
| [docs/security.md](docs/security.md) | 安全规则全文（红线之外的细则） |
| [USER_PREFERENCES.md](USER_PREFERENCES.md) | 项目负责人长期协作偏好（语言、plan、GitHub 提交语义） |

### 按场景按需读取（just-in-time retrieval）

| 你在做什么 | 读哪个文档 |
|---|---|
| **先建立架构全局认知（推荐入口）** | **[docs/architecture.md](docs/architecture.md)** — 单页总览，含分层图 + DAG 流转图；细节再按需 grep PRD 对应节，不要通读 1800 行 PRD |
| 选型 / 加依赖 / 部署相关 | [docs/tech-stack.md](docs/tech-stack.md) |
| 写 Agent / 修改 DAG / 触碰 Schema | [docs/constraints.md](docs/constraints.md) + PRD §六, §七 |
| **写 Python / TypeScript 代码（每次）** | **[docs/code-style.md](docs/code-style.md)** — 拿满代码风格分必读 |
| 提交代码 / 创建 PR / 管理分支 | [docs/git-workflow.md](docs/git-workflow.md) — Conventional Commits |
| 部署 / 配 LangSmith 等生产环境变量 | [docs/deployment.md](docs/deployment.md)（骨架，随部署补全） |
| 准备交付技术材料 / 数据库 ER 图 | [docs/database-er-diagram.md](docs/database-er-diagram.md) |
| 写测试 | [docs/testing.md](docs/testing.md) |
| 准备访谈 / 找演示案例 | [docs/collaboration-hankel.md](docs/collaboration-hankel.md) |
| 准备答辩 / 查评分维度与材料清单 | [docs/defense-requirements.md](docs/defense-requirements.md) — 答辩流程 + 5 维度评分卡 + 材料清单 |
| 整理 AI 协作证据 | [docs/ai-collaboration.md](docs/ai-collaboration.md) |

### 项目内部状态文件（**不是 Claude Code 的工作记忆**）

> ⚠️ 以下文件是「被构建的多 Agent 竞品分析系统」的**应用层运行时状态**，**不是 Claude Code 这个 harness 的记忆系统**。
> Claude Code 默认不需要主动读写它们，除非在调试本系统的 LangGraph workflow 本身。

| 文件 | 说明 |
|---|---|
| [claude-progress.txt](claude-progress.txt) | 项目开发进度日志（人工 / 里程碑更新） |
| [agent-states/](agent-states/) | Collector / Analyst / Writer / QA 4 个业务 Agent 的运行时状态（JSON） |
| [docs/agent-states-guide.md](docs/agent-states-guide.md) | 上述状态文件的 schema 与维护指南 |

---

## 四、比赛 10% 评分承诺：代码质量与文档（目标拿满）

[ai竞品分析要求.txt](ai竞品分析要求.txt) 评分卡 "代码质量与文档" 4 个子项，本项目对应规则：

| 评分子项 | 对应规则 / 文档 | 触发时机 / 验收 |
|---|---|---|
| **① 代码风格、模块化、注释、可读性** | [docs/code-style.md](docs/code-style.md) | 提交前必须：前端 `npm run lint` 0 error；后端 `ruff check` + `mypy` 全通过。**注释默认不写**，只写"为什么"非显然时（隐藏约束 / 性能权衡 / 外部 bug 绕过）。模块化按 PRD §十五 路径约定 |
| **② 项目文档齐全（README / 架构图 / Agent 协议 / 部署说明）** | `README.md`（项目根 ⚠️ **待写**）+ [docs/architecture.md](docs/architecture.md)（架构图，已抽出）+ PRD §六（Agent 协议）+ [docs/deployment.md](docs/deployment.md)（骨架已建，随部署补全） | 每个 P0 模块上线同步更新对应文档；改架构 → 更 PRD §五；改 Agent → 更 PRD §六 |
| **③ Git 提交规范、分支管理清晰** | [docs/git-workflow.md](docs/git-workflow.md) — Conventional Commits | 每条 commit message 符合 `<type>: <subject>` 规范（`feat:` / `fix:` / `docs:` …）；不直接 push main，过 PR；分支名 `feature/<topic>` |
| **④ AI 编程工具使用痕迹清晰** | 每条 AI 协作的 commit 末尾必须带 `Co-Authored-By: <Tool> <noreply@…>` 标注；PR 描述写明 AI 辅助的具体环节 | 答辩前用 `git log --grep="Co-Authored-By"` 一键导出所有 AI 协作记录作为佐证 |

**最容易丢分的两个点**（自我盯紧）：
- ② **项目根 `README.md` 还没写** —— 答辩前必须有，建议 Week 0.5 脚手架完就写第一版（项目简介 + 快速启动 + 链到 PRD / 架构图）
- ④ 忘记加 `Co-Authored-By` —— 建议配 git commit template 或 pre-commit hook 强制

---

## 五、工作规范（高阶原则）

1. **新会话先读偏好与进度**：每次开启新对话 / 新 Agent 接手时，先读取 [USER_PREFERENCES.md](USER_PREFERENCES.md) 与 [claude-progress.txt](claude-progress.txt) 顶部摘要，再开始任务
2. **PRD 是唯一事实源**：任何具体决策（功能 / Schema / 优先级 / 技术选型）以 [docs/PRD.md](docs/PRD.md) 为准，不要凭对话上下文猜需求
3. **按需读取**：开始任务前从 §三 表格找到相关文档，**只读这次任务需要的那几个**，不要预加载全部
4. **遇到歧义就停下来**：与其改错代码再回滚，不如先和项目负责人对齐——AskUserQuestion / 评论 / Issue 都行
5. **小步提交**：单次改动控制在 1 个 feature 内，commit message 遵循 [docs/git-workflow.md](docs/git-workflow.md)
6. **维护项目状态**：完成一个 Agent 任务 → 更新对应 `agent-states/*.json`；重要里程碑 → 同步 `claude-progress.txt`。详见 [docs/agent-states-guide.md](docs/agent-states-guide.md)
   - **每天第一次对话**：读取 [claude-progress.txt](claude-progress.txt)，确认「更新历史」最后一条日期 = 昨天（或更近）。如果落后，主动补录昨日完成的工作后再开始当天任务
7. **改动 = 同步更新文档**：架构改了 → 更 PRD §五；Schema 改了 → 更 PRD §七；Agent 协议改了 → 更 PRD §六；新增 `docs/` 文档 → 更新本文件 §三 索引
8. **前端设计 / 重构必走 skill**：任何前端组件、页面、UI 设计或重构任务（在 [frontend/](frontend/) 下），**开工前必须先调用** `frontend-design` 和 `web-design-guidelines` 两个 skill——前者生成有设计感的代码、避免 generic AI 风格，后者按 Vercel Web Interface Guidelines 做 a11y / 可用性 / typography 合规审查。两者按需挑选，不要跳过
9. **提 PR 前必须本地跑通 lint**：`git push` 发起 GitHub PR 前，本地必须跑 `npm run lint`（前端）/ `ruff check` + `mypy`（后端）**0 error 才能 push**。让 CI 失败的 PR 浪费 review 时间，也丢比赛 ③ 子项的 Git 规范分
