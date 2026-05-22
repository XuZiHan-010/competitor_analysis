# Git 工作流规范

> **本文档规范了项目的 Git 提交规范、分支管理和发布流程，确保代码历史清晰可追踪。**

## 1. 提交信息规范

### 格式：Conventional Commits

所有提交必须遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 分类

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新增功能或 Agent | `feat(collector-agent): implement web scraping` |
| `fix` | 修复 bug | `fix(analyzer-agent): correct pricing calculation logic` |
| `refactor` | 代码重构 | `refactor(schema): consolidate competitor models` |
| `docs` | 文档更新 | `docs(agent-protocol): document collector-analyzer handoff` |
| `test` | 测试相关 | `test(collector): add unit tests for data extraction` |
| `chore` | 构建、依赖更新 | `chore(deps): upgrade langraph to 0.2.0` |
| `style` | 代码格式（不改逻辑） | `style: remove trailing whitespace` |
| `perf` | 性能优化 | `perf(writer): optimize report generation speed` |

### Scope 分类

`<scope>` 应该是受影响的模块，通常为 Agent 名字或模块名：

- `collector-agent`：采集 Agent
- `analyzer-agent`：分析 Agent
- `writer-agent`：撰写 Agent
- `reviewer-agent`：质检 Agent
- `orchestrator`：编排框架（LangGraph DAG）
- `schema`：知识 Schema 定义
- `api`：后端 API
- `frontend`：前端交互
- `infra`：基础设施、部署

### Subject 规则

1. 使用**祈使句**：`implement`，不要 `implemented` 或 `implements`
2. **不要**大写首字母：`implement` 不是 `Implement`
3. **不要**加句号：`implement web scraping` 不是 `implement web scraping.`
4. **限制长度**：50 个字符以内

### Body 规则（可选但推荐）

- 解释 **为什么** 做这个改动，不要解释 **做了什么**（代码会说话）
- 每行 72 个字符以内，便于在 GitHub 上阅读
- 可以写多个段落，用空行分隔

### Footer 规则

用于引用相关的 Issue、PR 或其他信息：

```
Closes #123
Refs #456
Breaking-Change: description of breaking change
Co-Authored-By: Name <email@example.com>
```

### 例子

#### 简单提交
```
feat(collector-agent): add robots.txt compliance checker
```

#### 详细提交
```
feat(collector-agent): implement web scraping for competitor data

- Added BeautifulSoup integration for HTML parsing
- Implemented robots.txt compliance check before scraping
- Added automatic retry logic for rate-limited requests
- URL tracking for source attribution in final report

This is required for the collector agent to autonomously gather
competitor information from public websites without violating
terms of service.

Closes #15
```

#### 修复提交
```
fix(analyzer-agent): correct SWOT strength identification

Previously, strengths were incorrectly categorized as opportunities
due to logic error in the comparison matrix. Now using explicit
conditions to distinguish strengths (vs self) from opportunities
(vs market).

Fixes #42
```

#### 重构提交
```
refactor(schema): consolidate competitor models

Merged CompetitorProfile and CompetitorSnapshot into a single
CompetitorRecord with versioning support. This reduces duplication
and simplifies the analyzer-agent's input handling.

Breaking-Change: CompetitorSnapshot interface removed, use CompetitorRecord instead
```

## 2. 分支管理策略

### 分支命名规范

```
<type>/<description>
```

#### 分支类型

| 分支类型 | 用途 | 命名示例 | 来源 | 目标 |
|--------|------|--------|------|------|
| `main` | 生产分支（答辩版本） | - | PR from develop | - |
| `develop` | 开发主分支 | - | 所有 feature/fix 分支 | main |
| `feature/*` | 新功能/新 Agent | `feature/agent-collector`, `feature/langgraph-dag` | develop | develop |
| `fix/*` | bug 修复 | `fix/pricing-calculation`, `fix/source-tracking` | develop | develop |
| `docs/*` | 文档更新 | `docs/api-protocol`, `docs/deployment-guide` | develop | develop |
| `refactor/*` | 代码重构 | `refactor/schema-design`, `refactor/error-handling` | develop | develop |
| `test/*` | 测试相关 | `test/collector-agent`, `test/feedback-loop` | develop | develop |

### 示例分支列表

**第 0.5 周（架构设计）**：
- `feature/langgraph-orchestration`
- `feature/schema-design`
- `docs/architecture`

**第 1 周（Agent 单体开发）**：
- `feature/agent-collector`
- `feature/agent-analyzer`
- `feature/agent-writer`
- `feature/agent-reviewer`
- `test/collector-agent`
- `test/analyzer-agent`

**第 1.5 周（联调与反馈闭环）**：
- `fix/collector-analyzer-handoff`
- `fix/feedback-loop-logic`
- `test/integration-e2e`
- `docs/agent-protocol`

**第 2 周（答辩准备）**：
- `docs/deployment-guide`
- `docs/api-reference`
- `refactor/code-quality`

## 3. 工作流程

### 3.1 创建新分支

```bash
# 确保在 develop 分支上
git checkout develop
git pull origin develop

# 创建新分支
git checkout -b feature/agent-collector

# 建议：在分支上设置 tracking
git push -u origin feature/agent-collector
```

### 3.2 开发过程中的提交

```bash
# 频繁提交，保持原子性（一个提交 = 一个逻辑单元）
git add src/collector_agent.py
git commit -m "feat(collector-agent): implement BeautifulSoup scraper"

git add src/compliance.py
git commit -m "feat(collector-agent): add robots.txt checker"

# 不要用 git add -A 或 git add .
# 显式指定要提交的文件
```

### 3.3 发起 Pull Request

**PR Title**：遵循 Conventional Commits 格式，长度 < 70 字符

```
feat(collector-agent): implement web scraping with robots.txt compliance
```

**PR Description**：包含以下信息

```markdown
## 📝 Description
用一句话总结这个 PR 的目的。

## 🎯 Motivation & Context
为什么需要这个改动？解决了什么问题？

## 🔍 Changes Made
- 新增采集 Agent 的 web scraper 模块
- 实现 robots.txt 合规性检查
- 添加重试逻辑处理速率限制

## ✅ How to Test
1. 运行单元测试：`pytest tests/collector_agent/test_scraper.py`
2. 手动验证：`python -m src.collector_agent --test-url https://example.com`

## 📊 Testing Coverage
- Unit tests: 8/8 passed
- Integration tests: 3/3 passed

## 🔗 Related Issues
Closes #15
Refs #12

## 🎨 Screenshots / Output (if applicable)
```

### 3.4 代码审查

**审查者检查清单**：
- [ ] 提交信息遵循 Conventional Commits 格式
- [ ] 代码改动逻辑清晰，注释充分
- [ ] 有相应的测试
- [ ] 没有引入新的依赖或安全问题
- [ ] 文档是否需要更新

**提交者回应审查**：
```bash
# 根据反馈修改代码
# 不要 amend！创建新的 commit
git add src/collector_agent.py
git commit -m "fix(collector-agent): handle edge case in robots.txt parsing"

# 推送更新
git push origin feature/agent-collector
```

### 3.5 合并 PR

**自动化规则**（在 GitHub 上配置）：
- 至少 1 个审查者同意
- 所有 CI checks 通过
- 分支已更新到最新的 develop

**合并方式**：
- 推荐 **Squash and Merge**（保持 main/develop 分支历史简洁）
- 对于大型特性，可用 **Create a merge commit**

```bash
# 本地清理已合并的分支
git branch -d feature/agent-collector
git push origin --delete feature/agent-collector
```

## 4. 版本标记和发布

### 发布流程

当完成一个重要里程碑时（如"MVP 完成"、"答辩版本"），创建一个 tag：

```bash
# 切换到 main 分支
git checkout main
git pull origin main

# 创建 tag
git tag -a v1.0-mvp -m "MVP with all 4 agents working"
git tag -a v1.1-feedback-loop -m "Feedback loop and reviewer agent integration"

# 推送 tag
git push origin v1.0-mvp v1.1-feedback-loop
```

### Tag 命名规范

```
v<major>.<minor>-<milestone>
```

- `v1.0-architecture` — 架构设计完成
- `v1.0-agents-done` — 所有 Agent 单体开发完成
- `v2.0-mvp` — 端到端流程可运行
- `v2.1-feedback-loop` — 反馈闭环工作
- `v3.0-production` — 答辩版本

## 5. 与 claude-progress.txt 的关联

每次 merge 重要的 PR 时，更新 `claude-progress.txt`：

```bash
# 在本地编辑 claude-progress.txt
# 记录完成的里程碑、当前进度等

# 然后提交一个 housekeeping commit
git add claude-progress.txt
git commit -m "chore: update progress after agent-collector completion"
git push origin develop
```

## 6. 常用命令速查

```bash
# 查看分支列表
git branch -a

# 查看提交历史（简洁格式）
git log --oneline --graph --all

# 查看某个提交的详细信息
git show abc1234

# 查看特定 Author 的提交
git log --author="Name" --oneline

# 查看最近 N 次提交中修改了哪些文件
git log -N --name-status --oneline

# 检查哪些分支已经合并到 develop
git branch --merged develop

# 创建本地分支并跟踪远程分支
git checkout --track origin/feature/xxx

# 重新 base 分支（变基，用于保持线性历史）
git rebase develop
```

## 7. 常见场景

### 场景 1：我提交到了错误的分支

```bash
# 撤销最后的 commit（保留文件改动）
git reset --soft HEAD~1

# 切换到正确的分支
git checkout feature/correct-branch

# 重新提交
git commit -m "correct message"
```

### 场景 2：我要改写上个 commit 的信息

```bash
# 仅改 commit message
git commit --amend -m "new message"
git push origin branch --force-with-lease  # 谨慎使用，不要在 main/develop 上用
```

### 场景 3：我要合并 develop 的最新改动到我的 feature 分支

```bash
# 方案 A：merge（更安全，保留完整历史）
git merge develop

# 方案 B：rebase（保持线性，但改写历史）
git rebase develop
```

## 8. 安全检查清单

**提交前必须检查**：

- [ ] 没有提交 `.env` 或敏感文件（运行 `git diff --cached`）
- [ ] 提交信息遵循规范（type, scope, 祈使句）
- [ ] 代码通过了本地测试
- [ ] 没有硬编码 API key 或密钥
- [ ] 文档（README、AGENTS.md 等）已同步更新

**Push 前必须检查**：

- [ ] 分支名符合规范
- [ ] 本地最新（`git pull` 后再 push）
- [ ] 没有意外的大文件被提交（运行 `git log --name-status -1`）

---

**最后更新**: 2026-05-22
