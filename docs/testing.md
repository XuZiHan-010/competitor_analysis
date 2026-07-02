# 测试策略

---

## 测试金字塔（本项目版本）

```
        /\
       /  \    端到端 (1-2 个)
      /────\
     /      \   集成测试 (每个 Agent + DAG 串通)
    /────────\
   /          \  单元测试 (Pydantic Schema / 工具函数)
  /────────────\
```

---

## 后端 (FastAPI + LangGraph)

### 单元测试

- 工具：`pytest` + `pytest-asyncio`
- 范围：
  - 每个 Pydantic Schema 的字段验证
  - 工具函数（搜索 wrapper / 抓取器 / 导出器）
  - 每个 Agent 节点（**mock LLM**，验证 prompt 构造与输出解析）

### 集成测试

- 范围：
  - 空 PostgreSQL + pgvector 数据库执行 Alembic upgrade / check / downgrade
  - User / Task / Run / Trace / Report / Claim / Source 持久化往返、账户隔离、回滚和级联删除
  - pgvector 写入与检索机制、Redis Stream 重连和清理
  - DB 持久化路径必须落表，禁止以静默回退内存的结果冒充通过
- 本地与 PR CI 使用 `pgvector/pgvector:pg16` + Redis 7.4 临时服务，不连接 Neon / Upstash。
- 本地启动：`docker compose -f docker-compose.test.yml up -d`。
- 测试进程只读取 `TEST_DATABASE_URL` / `TEST_REDIS_URL`，且会拒绝生产式地址。

### 测试分层命令

在 `backend/` 下执行：

```bash
pytest -m unit
pytest -m integration
pytest -m smoke
pytest --cov=. --cov-branch
```

- 未显式标记的现有测试自动归入 `unit`。
- `integration` 需要临时 PostgreSQL + pgvector 和 Redis。
- `smoke` 只面向独立 Neon Branch / Upstash 测试实例，需显式设置 `SMOKE_ALLOW_REMOTE=true`。

### Mock LLM 策略

不要每次 CI 都真打 OpenAI（费钱 + 不稳定）：
- 用 `vcr.py` 录制真实响应到 fixture，CI 回放
- 关键 prompt 变更后重新录制

---

## 前端 (Next.js)

### 单元测试

- 工具：`vitest` + `@testing-library/react`
- 范围：关键组件（DAG viewer、溯源面板、报告 section）

### E2E 测试

- 工具：`playwright`
- 至少 1 个用例：
  ```
  访问首页 → 登录 → 创建任务 → 等待 DAG 跑完 → 查看报告 →
  点击溯源图标 → 看到原文片段 → 导出 PDF
  ```

---

## CI 触发

- PR 创建 / 更新 → Ruff → Mypy → Mock LLM 单元测试 → 临时 PostgreSQL/Redis 集成测试。
- 覆盖率启用 branch coverage，仅作为可见性指标，不设 100% 门槛。
- 每日定时或人工触发 `smoke-backend.yml`，使用 GitHub `smoke` environment 中的独立测试连接；该 workflow 不接受 PR 触发，因此 fork PR 无法消费 secrets。
- Smoke workflow 安装 Chromium，并执行真实 PDF 渲染；普通 PR 不安装浏览器、不打真实 LLM。

---

## 不做的事

- ❌ 不追求 100% 覆盖率：竞赛项目，时间有限
- ❌ 不为 Pydantic 字段写显然的测试（如 `assert model.field == "x"`）
- ❌ 不在测试里调真实 OpenAI（除了人工触发的 smoke test）

---

## 演示前的 Smoke Test

3 周末答辩前必须跑一遍：

- [ ] 完整端到端：登录 → 创建任务 → 看报告 → 导出 PDF + PPTX
- [ ] 反馈闭环演示路径（故意构造缺失数据触发 QA 打回）
- [ ] DAG 可视化无渲染异常
- [ ] 溯源跳转无 404
- [ ] PDF / PPTX 在主流软件中无排版问题（Adobe Reader / PowerPoint）
