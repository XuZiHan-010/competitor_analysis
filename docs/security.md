# 安全红线

> **AI Agent 与人类开发者都必须遵守。违反任何一条 = 立即停下来与项目负责人确认。**

---

## 🔴 红线 1：包含 env 的文件绝对不可以上传到 GitHub 或外泄

### 不可入库的文件清单

- `.env`
- `.env.local`
- `.env.development`
- `.env.production`
- 任何带 `secret` / `credentials` / `key` / `token` 字样的文件
- Railway / Neon / Upstash / OpenAI / Tavily 的 API key / 连接字符串

### 强制规则

1. **`.gitignore` 必须在仓库初始化时第一时间配好**，包含：
   ```
   # Env & secrets
   .env
   .env.*
   !.env.example
   *.pem
   *.key
   secrets/
   credentials/
   ```
2. **`.env.example` 可以入库**，但只含 key 名称，**不含** 任何真实值
3. **commit 前必须检查**：`git diff --cached` 看一眼，发现疑似密钥立即 `git restore --staged`
4. **发现已被 commit 的密钥**：
   - 立刻**轮换密钥**（在对应平台重新生成）
   - 不要试图用 `git reset` 掩盖，密钥已泄露
   - 使用 `git filter-repo` 或 BFG 从历史中清除（仅止血，不解决泄露）

### 不可外泄的范围（超出 GitHub）

- 不要把密钥贴到 Slack / 微信 / 邮件
- 不要把密钥贴到 ChatGPT / Claude.ai / 其他在线 AI 工具
- 不要把密钥写到任何文档（包括本地 markdown）
- 不要在演示视频 / 截图中暴露密钥（截图前关闭终端中的 env 显示）

---

## 🔴 红线 2：所有密钥走环境变量

- 本地开发：`.env`（被 `.gitignore` 排除）
- Railway：用平台的 Environment Variables UI
- Neon / Upstash：用各平台提供的连接字符串，注入到 Railway 的 env 中
- **代码里禁止任何形式的硬编码**：
  ```python
  # ❌ 错误
  OPENAI_API_KEY = "sk-..."

  # ✅ 正确
  import os
  OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
  ```

---

## 🟡 黄线：用户数据合规

虽然本项目不直接采集真实用户隐私（问卷为模拟），仍要做到：

1. **登录用户的邮箱**：仅用于发验证码与关联报告，**不发营销邮件**
2. **采集的网页内容**：尊重目标站点的 robots.txt 与服务条款
3. **如果未来接入真实用户访谈数据**：必须脱敏（去掉姓名 / 手机 / 邮箱）后再入库
4. **日志中的敏感字段**：API key / JWT / 密码必须打码（如 `sk-***`）
5. **LangSmith trace 上报**（[PRD §五.Y 约束 6](PRD.md#L188)）：竞品公开网页数据可全量上报；但 **SurveyTool 涉敏节点（访谈 / 用户声音 / persona）必须用 `hide_inputs`/`hide_outputs` 或 anonymizer 脱敏后再上报**。`LANGCHAIN_API_KEY` 走 env 不入库；CI 默认关闭 trace 上报，仅本地 debug / 答辩演示时开启

---

## 自检清单（每次 commit / push 前）

- [ ] `git status` 不显示 `.env*`（除 `.env.example`）
- [ ] `git diff --cached` 没有形如 `sk-xxx` / `postgresql://user:pass@...` / `https://...up.railway.app/...?token=` 的字符串
- [ ] 新增依赖不引入任何会自动上报数据的 telemetry SDK（**例外**：LangSmith 是受控接入，受 env 开关 + 涉敏脱敏约束，见黄线第 5 条）
- [ ] 日志输出（特别是 Trace 表）没记录原始 API key

---

## 紧急响应：如果密钥已泄露

1. **立即轮换**：到对应平台（OpenAI / Tavily / Neon / Upstash / Railway）重新生成密钥
2. **删除旧密钥**：确保旧密钥在平台侧失效
3. **通知项目负责人**：说明泄露范围（哪些文件、commit 到哪个分支、是否 push 到远程）
4. **清理历史**（仅止血）：`git filter-repo` 移除历史中的密钥行，force push
5. **复盘**：在 [docs/PRD.md](PRD.md) 或本文件追加"已知事件"段落，写明根因与改进
