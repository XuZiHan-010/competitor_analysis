# AGENTS.md

> **本文件是所有 AI 编程 Agent 的统一入口**（Codex / Claude Code / Cursor / Aider / TRAE 等通用）。
> [CLAUDE.md](CLAUDE.md) 只是一个 1 行指针，指向本文件，避免内容漂移。
> 内容分三部分：① 安全红线（必须遵守），② 目录索引（按需读取），③ 工作规范（高阶原则）。

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
- 不要散落在项目其他位置（如 `apps/api/plan.md`）
- 命名建议：`YYYY-MM-DD-<topic>.md`
- 详见 [plans/README.md](plans/README.md)

---

## 二、文档索引（与 CLAUDE.md 等价）

### 任何工作前必读

| 文档 | 说明 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | 完整产品需求文档（v1.0）—— 唯一事实源 |
| [ai竞品分析要求.txt](ai竞品分析要求.txt) | 比赛官方课题与评分标准 |
| [docs/security.md](docs/security.md) | 安全规则全文（红线之外的细则） |

### 按场景按需读取（just-in-time retrieval）

| 你在做什么 | 读哪个文档 |
|---|---|
| 选型 / 加依赖 / 部署相关 | [docs/tech-stack.md](docs/tech-stack.md) |
| 写 Agent / 修改 DAG / 触碰 Schema | [docs/constraints.md](docs/constraints.md) + PRD §6, §7 |
| 写 Python / TypeScript 代码 | [docs/code-style.md](docs/code-style.md) |
| 提交代码 / 创建 PR | [docs/git-conventions.md](docs/git-conventions.md) |
| 写测试 | [docs/testing.md](docs/testing.md) |
| 准备访谈 / 找演示案例 | [docs/collaboration-hankel.md](docs/collaboration-hankel.md) |

### 待创建（开发过程中填充）

| 文档 | 何时创建 |
|---|---|
| `docs/architecture.md` | Week 0.5 脚手架搭完后 |
| `docs/agent-protocol.md` | Week 1 第一个 Agent 落地后 |
| `docs/schemas.md` | Week 0.5 Pydantic 落地后 |
| `docs/deployment.md` | Week 2 首次部署 Railway 后 |

> **新增 / 重命名 docs/ 下任何文档时，必须同步更新本索引和 [CLAUDE.md](CLAUDE.md)。**

---

## 三、工作规范（高阶原则）

### 1. PRD 是唯一事实源
任何具体决策（功能、Schema、优先级、技术选型）以 [docs/PRD.md](docs/PRD.md) 为准，不要凭对话上下文猜需求。

### 2. 按需读取，不要预加载
本索引设计为 **just-in-time retrieval**：开始任务前先从 §二 表格找到相关文档，**只读** 你这次任务需要的那几个。不要一次性读完所有 docs。

### 3. 遇到歧义就停下来
与其改错代码再回滚，不如先与项目负责人对齐。AskUserQuestion / 评论 / Issue 都行。

### 4. 小步提交
单次改动控制在 1 个 feature 内。Commit message 遵循 [docs/git-conventions.md](docs/git-conventions.md)。

### 5. 改动 = 同步更新文档
- 改了架构 → 更新 `docs/architecture.md`
- 改了 Schema → 更新 `docs/schemas.md` 和 PRD §7
- 改了 Agent 协议 → 更新 `docs/agent-protocol.md` 和 PRD §6
- 新增了重要文档 → 更新本文件 §二 索引表

### 6. plan 文件放在 [plans/](plans/)
见 §一 红线 2 与 [plans/README.md](plans/README.md)。

### 7. 安全红线
见 §一。**包含 env 的文件、API key、密钥连接字符串：绝对不可入库、不可外泄。**

---

**最后更新：2026-05-22**
