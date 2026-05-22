# Agent 状态存储目录

## 概述

此目录存储各个 Agent 的实时状态文件（JSON 格式）。这是根据 Anthropic《Effective harnesses for long-running agents》推荐的架构——**Agent 的状态应该外化到文件系统，而不是存在上下文窗口里**。

## 文件列表

```
agent-states/
├── collector-agent-state.json    # 采集 Agent 状态
├── analyzer-agent-state.json     # 分析 Agent 状态
├── writer-agent-state.json       # 撰写 Agent 状态
├── reviewer-agent-state.json     # 质检 Agent 状态
└── README.md                      # 本文件
```

## 使用场景

### 1. **系统启动恢复**
当系统重启或从中断恢复时，Agent 通过读取自己的状态文件来了解：
- 当前处理的竞品是什么
- 哪些任务已完成
- 哪些任务待处理
- 上次是在哪一步卡住的

### 2. **Agent 之间的交接**
Agent A 完成任务后，Agent B 需要快速理解前置工作：
- Collector → Analyzer：采集了哪些竞品的哪些数据
- Analyzer → Writer：完成了哪些分析维度
- Writer → Reviewer：哪些报告待审核

### 3. **反馈闭环**
质检 Agent 发现问题时：
- 在 `reviewer-agent-state.json` 记录反馈
- 在 `collector-agent-state.json` 中标记该竞品为"待重做"
- Collector Agent 启动后看到"待重做"标记，立刻知道要重新采集哪些数据

### 4. **可观测性**
每个 Agent 的 `recent_activities` 和 `errors` 字段记录：
- 决策过程
- Token 消耗
- 数据源
- 错误日志

## 状态文件更新原则

✅ **应该做**：
- 频繁更新（任务完成后立刻更新，不要等）
- 每次更新都是完整的（原子操作）
- 保留完整的 `recent_activities` 历史
- 记录 `last_updated` 时间戳

❌ **不应该做**：
- 只更新部分字段（导致信息不一致）
- 删除历史记录
- 硬编码 Agent 名字或路径

## 与其他文件的关系

| 文件 | 用途 | 更新频率 |
|------|------|--------|
| `claude-progress.txt` | 系统全局进度摘要 | 每周或每个里程碑 |
| `agent-states/*.json` | 各 Agent 的实时状态 | 每个任务完成后 |
| `.gitignore` | 排除敏感文件 | 不需要更新 |
| `docs/git-workflow.md` | Git 提交规范 | 不需要更新 |

## 快速开始

### 如果你是 Agent 开发者

```python
import json
from datetime import datetime
from pathlib import Path

def load_my_state():
    state_file = Path('agent-states/collector-agent-state.json')
    with open(state_file) as f:
        return json.load(f)

def save_my_state(state):
    state['last_updated'] = datetime.now().isoformat()
    state_file = Path('agent-states/collector-agent-state.json')
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

# 启动时加载状态
state = load_my_state()
pending = state['pending_competitors']
print(f"Resuming with pending competitors: {pending}")

# 处理完后更新状态
state['completed_tasks'].append('ChatGPT')
state['pending_competitors'].remove('ChatGPT')
save_my_state(state)
```

### 如果你是系统管理员

查看全局进度：
```bash
cat claude-progress.txt | grep "状态:"
```

检查各 Agent 的状态：
```bash
ls -lah agent-states/*.json
```

查看最近的反馈闭环：
```bash
grep "feedback_issued" agent-states/reviewer-agent-state.json
```

## 详细文档

完整的使用指南和最佳实践见：[docs/agent-states-guide.md](../docs/agent-states-guide.md)

---

**最后更新**: 2026-05-22
