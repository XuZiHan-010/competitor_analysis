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
  - LangGraph DAG 从 `CollectorAgent` 跑到 `QAAgent`（用录制好的 LLM 响应回放）
  - 反馈闭环：构造缺失字段 → QA 打回 → 重跑 → 字段填充
- 工具：`pytest` + `respx`（mock OpenAI/Tavily HTTP）

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

- PR 创建 / 更新 → 跑所有单元 + 集成测试
- merge 到 `main` → 跑 E2E（部署到 Railway preview 后）

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
