# Git 协作约定

---

## 分支策略

| 分支 | 用途 | 保护 |
|---|---|---|
| `main` | 生产分支，对应 Railway 生产部署 | 保护，禁止 force push |
| `dev` | 集成分支，所有 feature 先合到这里 | 保护 |
| `feature/<name>` | 功能分支 | 自由开发 |
| `fix/<name>` | Bug 修复 | 自由开发 |
| `docs/<name>` | 纯文档改动 | 自由开发 |

**禁止**：直接 push 到 `main`。所有变更走 PR → review → merge。

---

## Commit Message

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### type 取值

| type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | bug 修复 |
| `docs` | 仅文档 |
| `refactor` | 重构（不改行为） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/依赖/工具链 |

### 示例

```
feat(agent): add CollectorAgent search tool
fix(qa): correct retry counter when blocker resolved
docs(prd): update section 14.1 with survey questions
refactor(graph): extract checkpointer to db module
```

### AI 协作署名

如果 commit 是 AI 协作产物（Claude Code / Codex / TRAE），在 footer 加：

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

**理由**：评分项"TRAE / AI 编程工具使用痕迹清晰"。

---

## PR 规范

### 标题
跟 commit 一样的 `<type>(<scope>): <subject>` 格式。

### Body 模板

```markdown
## 改了什么
（1-3 句话）

## 为什么
（关联到 PRD 哪一节 / Issue 编号）

## 怎么测
- [ ] 单元测试通过
- [ ] 端到端测试通过：登录 → 创建任务 → 看报告
- [ ] 文档同步更新（如适用）

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### Review 节奏

- feature PR：至少 1 个 reviewer approve
- docs PR：可以 self-merge（紧急时）
- 涉及 Agent 协议 / Schema / 数据库迁移：必须 2 人 review

---

## 禁止事项

- ❌ 不要用 `git commit --amend` 修改已 push 的 commit
- ❌ 不要 `git push --force` 到保护分支（main / dev）
- ❌ 不要在 commit message 里写密钥 / 邮箱 / 内部 URL
- ❌ 不要 `git add .` 或 `git add -A`：可能误加 `.env`，永远显式指定文件
- ❌ 不要 `--no-verify` 跳过 pre-commit hook（除非紧急且已与负责人确认）

---

## .gitignore 必须项

参见 [security.md](security.md) §红线 1。
