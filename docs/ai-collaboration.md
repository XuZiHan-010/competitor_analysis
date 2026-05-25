# AI 协作证据说明

> 本文档用于对应比赛评分项中的「TRAE 等 AI 编程工具的使用痕迹清晰，体现深度协作」。
> 目标不是证明“用了 AI”，而是证明本项目把不同 AI 工具纳入了真实的软件工程流程，并保留了可审计的协作证据链。

---

## 一、协作目标

本项目将 AI 编程工具视为分工明确的协作成员，而不是单次问答或代码补全工具。

我们希望评委能够看到三件事：

1. 不同 AI 工具有明确职责边界
2. AI 参与贯穿架构、实现、评审三个阶段
3. 协作过程在文档、提交记录、PR 和 review 中都有痕迹

---

## 二、工具分工

当前项目采用如下分工：

| 工具 | 主要职责 | 典型产物 |
|---|---|---|
| **Claude Code Opus 4.7** | 架构设计、PRD 演进、Agent 协议、系统拆解 | `docs/PRD.md`、架构章节、任务拆解草案 |
| **Claude Sonnet 4.6** | 前端页面开发、交互设计、组件细化、UI 重构 | `frontend/` 下页面与组件、交互优化提交 |
| **Codex** | 后端开发、FastAPI API、LangGraph DAG、Pydantic Schema、联调 | `backend/`、接口契约、状态流实现 |
| **TRAE** | 代码 review、风险检查、边界问题修复、小范围修改 | review 反馈、修复 commit、质量改进记录 |

> 人类开发者负责需求判断、优先级选择、最终提交与合并决策。AI 工具参与设计与实现，但不替代最终工程责任。

---

## 三、深度协作如何体现

### 1. 分阶段协作，而非单点使用

本项目中的 AI 协作不是“谁顺手写一点代码”，而是按软件工程阶段分工：

- **架构阶段**：Claude Code Opus 4.7 负责把需求沉淀为 PRD、Agent 边界、Schema 设计和系统流程
- **前端阶段**：Claude Sonnet 4.6 基于既定 PRD 和协议实现 UI、页面与交互细节
- **后端阶段**：Codex 根据同一份契约实现 API、状态流和后端模块
- **评审阶段**：TRAE 对现有改动做 review，识别风险和可改进点，再形成后续修复

这种方式体现的是“AI 与 AI 之间有上下游交接，且围绕统一文档协同推进”，而不是彼此孤立地产出代码。

### 2. 统一事实源驱动协作

所有工具都以 [docs/PRD.md](PRD.md) 为唯一事实源，以 [AGENTS.md](../AGENTS.md) 和 [docs/git-workflow.md](git-workflow.md) 为统一规则。

因此，协作链条是：

`PRD / 架构约束 → 前端实现 → 后端实现 → review 检查 → 修复提交`

评委能够从文档和代码中看到同一套设计约束被连续继承，而不是后期“拼装”出来的结果。

### 3. 工程痕迹可审计

我们要求所有 AI 协作都尽量留下结构化证据：

- Git commit footer 中的 `Co-Authored-By`
- PR 描述中的 `AI Assistance` 区块
- 文档中的设计决策记录
- review 后新增的修复提交

这些痕迹共同证明：

- 哪个工具参与了哪一类工作
- AI 参与的是设计、实现还是 review
- 协作是否贯穿整个开发流程

---

## 四、证据链规范

### 4.1 Git 提交记录

每个由 AI 参与的 commit，都应在 footer 中带上对应标记：

```text
Co-Authored-By: Claude Code Opus 4.7 <noreply@anthropic.com>
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Co-Authored-By: Codex <noreply@openai.com>
Co-Authored-By: TRAE <noreply@bytedance.com>
```

说明：

- 一个 commit 可以同时保留人类作者和 AI 协作 footer
- 不同模块尽量对应到最贴近的工具，而不是所有 commit 都写同一个 AI
- 这样导出历史时，能够按工具维度回溯协作范围

答辩前可用以下命令导出证据：

```bash
git log --grep="Co-Authored-By" --oneline
```

### 4.2 Pull Request 描述

每个重要 PR 建议包含 `AI Assistance` 区块，写清楚：

- 哪些工具参与了本次改动
- 各自负责什么
- 人类开发者做了哪些最终选择

推荐模板：

```md
## AI Assistance
- Claude Code Opus 4.7: refined PRD and architecture constraints
- Claude Sonnet 4.6: implemented frontend interaction updates
- Codex: implemented backend contracts and workflow logic
- TRAE: reviewed the change set and suggested follow-up fixes

## Human Decisions
- locked the core four schemas as MVP invariants
- kept manual report correction in P1
- used PRD as the single contract between frontend and backend
```

### 4.3 Review 与修复闭环

如果 TRAE 参与 review，建议不要只停留在口头检查，而要形成显式修复记录：

- review 发现问题
- 新增 `fix(...)` 提交
- PR 中说明这是针对 review 的响应

这样能证明 TRAE 的参与不是“挂名”，而是进入了工程闭环。

---

## 五、当前项目的推荐使用方式

结合本项目当前阶段，推荐采用如下协作路径：

1. **Claude Code Opus 4.7**：负责 PRD、架构和 Agent 协议演进
2. **Claude Sonnet 4.6**：负责 `frontend/` 下页面、组件、交互和视觉细化
3. **Codex**：负责 `backend/` 下 API、Schema、LangGraph 编排和联调
4. **TRAE**：在阶段性 PR 上执行 review，提出风险点和修复建议

对应到仓库中的证据形式：

- 文档更新提交：体现架构阶段协作
- 前端 feature 提交：体现交互实现阶段协作
- 后端 feature 提交：体现系统实现阶段协作
- review 修复提交：体现质量把关和闭环

---

## 六、答辩时如何展示

答辩材料中建议单独放一页「AI 深度协作证据」，展示以下内容：

1. 一张分工图
   - Claude Opus：架构
   - Sonnet：前端
   - Codex：后端
   - TRAE：review

2. 一段 Git 历史截图
   - 展示带 `Co-Authored-By` 的 commit

3. 一个 PR 截图
   - 展示 `AI Assistance` 和 review / fix 记录

4. 一段文档截图
   - 展示 PRD、架构文档或本文档中的协作说明

推荐讲解口径：

> 我们不是把 AI 当作简单代码补全工具，而是把不同模型放在架构、前端、后端和 review 四个阶段分工协作，并通过文档、提交历史、PR 和修复记录保留完整证据链。

---

## 七、最低验收标准

为了让这一评分项稳定拿分，至少满足以下条件：

- [ ] 关键 commit 带 `Co-Authored-By`
- [ ] 至少 1 个 PR 写明 AI 分工和辅助环节
- [ ] 至少 1 份文档明确记录 AI 协作方式
- [ ] 至少 1 次 review 有对应修复提交
- [ ] 答辩材料中单独展示 AI 协作证据

如果只有「commit 里出现 Eric + Codex / Claude」，可以证明“使用了 AI”，但还不足以完整体现“深度协作”。本文件的目标就是把这部分证据补齐。
