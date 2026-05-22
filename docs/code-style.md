# 代码风格

> 适用于 [apps/api](../apps/api) (Python) 和 [apps/web](../apps/web) (TypeScript)。

---

## Python (后端)

### 工具链

- **格式化**：`black`（line-length 100）
- **lint**：`ruff`（启用 `E`, `F`, `I`, `B`, `UP`, `SIM`）
- **类型检查**：`mypy`（关键函数必须类型注解；不强制 100% 覆盖）

### 规范

- 类型注解：所有公开函数 / Pydantic 模型 / Agent 入口都必须有完整类型
- 异常处理：仅在边界处 catch（API 入口、外部服务调用）；内部代码相信类型契约
- 日志：用 `structlog` 输出 JSON 格式，便于落 Trace 表
- LangGraph State：所有 State 字段用 Pydantic v2 模型，不要用 dict

### 命名

- 文件：`snake_case.py`
- 类：`PascalCase`
- 函数 / 变量：`snake_case`
- Agent 类名：`<Role>Agent`，如 `CollectorAgent`、`AnalystAgent`
- LangGraph 节点函数：`<verb>_<role>`，如 `run_collector`、`check_qa`

---

## TypeScript (前端)

### 工具链

- **格式化**：`prettier`（默认配置 + `singleQuote: true`）
- **lint**：`eslint`（用 `next/core-web-vitals` 推荐配置）
- **类型**：`tsconfig.json` 必须 `"strict": true`

### 规范

- 不允许 `any`：用 `unknown` + 类型守卫
- 组件用函数式，hook 优先
- API 调用统一封装到 `lib/api/`，不在组件里写 `fetch`
- Schema 类型从后端 OpenAPI 自动生成（用 `openapi-typescript`），不要手抄

### 命名

- 文件：组件 `PascalCase.tsx`；工具 `kebab-case.ts`
- React 组件：`PascalCase`
- hooks：`useXxx`
- 常量：`SCREAMING_SNAKE_CASE`

---

## 通用

### 注释

- **默认不写注释**。命名清楚的代码自解释
- **只在"为什么"非显然时写一行**：隐藏约束、外部 bug 绕过、性能权衡
- **不写**：`# 这里是采集 Agent` 这种 what 注释
- **不写**：引用任务编号 / 历史改动（这些信息在 git 历史中）

### Schema 设计

- Pydantic 模型与 TypeScript 类型保持同步（建议从 OpenAPI 单源生成）
- 字段命名：用 `snake_case`（Python/JSON）；TS 端可在边界转换为 `camelCase`，但建议直接保持 `snake_case` 减少转换

### 错误处理边界

- ✅ 在 API 路由入口 catch 异常，转成统一的错误响应
- ✅ 在外部服务调用（OpenAI / Tavily / Playwright）处加重试 + 超时
- ❌ 不要在每层函数里都 try/except 包一遍
- ❌ 不要 catch 后只 `pass`：日志至少要写

---

## Pre-commit 钩子（推荐配置）

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
  - repo: https://github.com/pre-commit/mirrors-prettier
    hooks:
      - id: prettier
```
