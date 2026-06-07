# 部署说明（deployment）

> ⚠️ 本文档为骨架，随 Week 2 正式部署逐步补全。当前仅落地 **LangSmith 可观测（生产）** 一节；
> Railway / Neon / Upstash 的完整部署步骤待部署落地后补。
>
> 安全前提（[AGENTS.md](../AGENTS.md) 红线 1）：所有密钥只在平台的 Variables / Secrets 里配置，
> **绝不写进仓库、文档、截图或演示视频**。`.env.example`（[backend/.env.example](../backend/.env.example) /
> [frontend/.env.example](../frontend/.env.example)）只含 key 名、不含真实值。

---

## LangSmith 可观测（生产）

生产环境对 LangGraph 每个 Agent 节点做 tracing，用于答辩展示与开发期 debug。
定位见 PRD §五「可观测三层分工」：LangSmith 是**增强层**，自建 `agent_traces` 表才是事实源，
报告权威性靠 `source_ids`——三者正交，LangSmith 不可替代后两者。

### 访问模型：org 受控可见（非全网公开）

- 后端 `LANGCHAIN_API_KEY` 只用于**上传** trace，**不等于读取授权**。
- 前端的 LangSmith 链接对未登录访客是登录墙（看不到任何内容）；
  **只有被邀请进本项目 LangSmith org 的成员**（你、队友、评委）登录后才能回放 trace。
- 因此「让评委点进去看」的正确做法 = 在 LangSmith 控制台把评委邀请进 org，
  **不是**把 key 暴露给前端，也**不开** Public Share（那会让 trace 全网可见）。

### 环境变量

| 位置 | 变量 | 值 / 说明 |
|---|---|---|
| 后端（Railway Variables） | `LANGCHAIN_TRACING_V2` | `true` 开启上传；CI / 本地默认 `false` 不出网 |
| 后端（Secret） | `LANGCHAIN_API_KEY` | 你的 LangSmith key，**只在 Railway Variables 配，绝不进仓库** |
| 后端 | `LANGCHAIN_PROJECT` | 建议 `competitor-analysis-prod`，与本地/demo project 分开 |
| 前端（Railway Variables） | `NEXT_PUBLIC_LANGSMITH_RUN_URL` | run 深链模板，含 `{run_id}`；缺省则链接只能跳到 dashboard 根 |
| 前端（可选） | `NEXT_PUBLIC_LANGSMITH_PROJECT_URL` | 报告页 project 级入口，缺省回退 RUN_URL origin / dashboard |

`NEXT_PUBLIC_LANGSMITH_RUN_URL` 取值：登录 LangSmith → 打开任一 run → 复制地址栏 URL →
把 run 段替换成 `{run_id}`，例如
`https://smith.langchain.com/o/<ORG_UUID>/projects/p/<PROJECT_UUID>/r/{run_id}`。

### 操作步骤

1. Railway 后端服务设 `LANGCHAIN_TRACING_V2`、`LANGCHAIN_API_KEY`、`LANGCHAIN_PROJECT`。
2. Railway 前端服务设 `NEXT_PUBLIC_LANGSMITH_RUN_URL`（填真实 org/project UUID）。
3. LangSmith 控制台 → Org → Members → 邀请队友/评委。
4. 跑一次任务，确认 LangSmith 对应 project 出现完整 trace，且报告/任务页 LangSmith 链接能跳到具体 run。

### 残留风险（已知情接受）

开启 tracing 后，每次 LLM 调用的输入/输出会实时发到 LangSmith（美国云）。
上传前经 [observability.py](../backend/services/observability.py) 的 `hide_inputs`/`hide_outputs`
钩子脱敏，但 [redaction.py](../backend/services/survey/redaction.py) **目前仅覆盖 邮箱 / 电话 /
「姓名:中文」三种模式**——竞品正文、问卷自由文本基本原样出境。竞品数据多为公开网络内容、风险低；
若问卷含受访者敏感信息需留意。后续降险方向：扩 `redact_sensitive_text` 模式，或对 survey 自由文本整段屏蔽。
