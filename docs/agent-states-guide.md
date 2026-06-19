# Agent 状态文件使用指南

> **本文档说明如何使用 `agent-states/` 目录中的状态文件来维护 Agent 系统的"长期记忆"。**

## 概述

根据 Anthropic 的《Effective harnesses for long-running agents》，Agent 的状态不应该存在上下文窗口里，而应该外化到文件系统。这样做的好处：

- 🧠 **长期记忆**：系统中断后，下一轮 Agent 从状态文件读出，立刻知道"现在到哪步了"
- 🔄 **Agent 交接**：Agent A 完成任务交给 Agent B，Agent B 通过状态文件理解前置工作
- 📊 **可观测性**：每个 Agent 的决策过程、中间结果、Token 消耗均可追溯
- 🔗 **反馈闭环**：质检 Agent 发现问题，记录在状态文件，打回采集 Agent 重做

## 目录结构

```
agent-states/
├── README.md                    # 本文件
├── collector-agent-state.json   # 采集 Agent 的实时状态
├── analyzer-agent-state.json    # 分析 Agent 的实时状态
├── writer-agent-state.json      # 撰写 Agent 的实时状态
└── reviewer-agent-state.json    # 质检 Agent 的实时状态
```

## 状态文件结构

### 公共字段（所有 Agent 都有）

```json
{
  "agent_name": "collector-agent",           // Agent 标识
  "agent_role": "信息采集 Agent",             // Agent 角色描述
  "version": "1.0",                          // 状态版本
  "last_updated": "2026-05-22T14:30:00Z",   // ISO 8601 时间戳
  "status": "idle|running|blocked|error",    // 当前状态
  "current_task": "task_id|null",            // 当前任务 ID
  "completed_tasks": [],                     // 已完成的任务列表
  "recent_activities": [],                   // 最近活动日志
  "errors": [],                              // 错误日志
  "next_action": "..."                       // 下一步行动
}
```

### 各 Agent 的专用字段

#### 1. Collector Agent（采集 Agent）

```json
{
  "active_competitors": ["ChatGPT", "Claude"],
  "pending_competitors": ["Perplexity", "..."],
  "data_sources": {
    "web": { "enabled": true, "method": "web scraping" },
    "api": { "enabled": false },
    "survey": { "enabled": false }
  },
  "extraction_schema": {
    "features": { "status": "completed", "fields": [...] },
    "pricing": { "status": "in_progress", "fields": [...] },
    "user_profiles": { "status": "pending", "fields": [...] }
  }
}
```

#### 2. Analyzer Agent（分析 Agent）

```json
{
  "analysis_tasks": {
    "feature_comparison": {
      "status": "in_progress",
      "completed_competitors": ["ChatGPT"],
      "in_progress": ["Claude"]
    },
    "pricing_analysis": { ... },
    "user_segment_analysis": { ... },
    "swot_analysis": { ... }
  },
  "comparison_matrix": {
    "status": "design",
    "dimensions": ["core_features", "pricing_model", ...]
  },
  "quality_checks": {
    "data_completeness": "passed",
    "consistency_validation": "in_progress"
  }
}
```

#### 3. Writer Agent（撰写 Agent）

```json
{
  "writing_tasks": {
    "executive_summary": {
      "status": "in_progress",
      "completed_competitors": ["ChatGPT"]
    },
    "detailed_comparison": { ... },
    "pricing_breakdown": { ... },
    "swot_report": { ... },
    "positioning_map": { ... }
  },
  "output_formats": {
    "markdown": { "enabled": true, "schema_version": "1.0" },
    "json": { "enabled": true, "schema_version": "1.0" },
    "html": { "enabled": false }
  }
}
```

#### 4. Reviewer Agent（质检 Agent）

```json
{
  "review_queue": ["report_1", "report_2"],
  "approval_status": {
    "passed": ["ChatGPT_report_v1"],
    "rejected_pending_rework": ["Claude_report_v1"],
    "awaiting_review": ["Perplexity_report_v1"]
  },
  "quality_checks": {
    "fact_verification": {
      "enabled": true,
      "criteria": ["source_attribution", "data_consistency", "currency_check"]
    }
  },
  "feedback_issued": [
    {
      "target_competitor": "Claude",
      "target_agent": "collector-agent",
      "issue": "定价模型字段缺失",
      "reason": "源页面可能有动态加载内容",
      "suggested_fix": "改用 Selenium 处理动态内容",
      "timestamp": "2026-05-22T14:30:00Z"
    }
  ],
  "feedback_closure": {
    "by_agent": {
      "collector-agent": {
        "issues_found": 2,
        "issues_resolved": 1,
        "success_rate": 0.5
      }
    }
  }
}
```

## 使用场景

### 场景 1：系统启动时恢复状态

```bash
# Agent 启动时读取自己的状态文件
python agent_collector.py --state agent-states/collector-agent-state.json
```

**Agent 代码示例**（伪代码）：
```python
import json
from pathlib import Path

def load_agent_state(state_file):
    with open(state_file) as f:
        state = json.load(f)
    
    # 从状态文件恢复
    pending_competitors = state['pending_competitors']
    last_task = state['current_task']
    
    print(f"Resuming from last task: {last_task}")
    print(f"Pending competitors: {pending_competitors}")
    
    return state

def save_agent_state(state, state_file):
    """每次任务完成后更新状态"""
    state['last_updated'] = datetime.now().isoformat()
    state['completed_tasks'].append(current_task)
    state['current_task'] = next_task
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
```

### 场景 2：Agent 之间的交接

**Collector → Analyzer**：
```python
# Analyzer 读取 Collector 的状态
collector_state = load_agent_state('agent-states/collector-agent-state.json')

# 获取已完成的采集数据
completed = collector_state['active_competitors']
pending = collector_state['pending_competitors']

print(f"Ready to analyze: {completed}")
```

### 场景 3：质检反馈闭环

**Reviewer 发现问题并打回**：
```python
# Reviewer Agent 发现问题
issue = {
    "target_competitor": "ChatGPT",
    "target_agent": "collector-agent",
    "issue": "定价字段缺失",
    "timestamp": datetime.now().isoformat()
}

# 1. 更新 reviewer 自己的状态
reviewer_state['feedback_issued'].append(issue)

# 2. 更新 collector 的状态：标记任务为 "pending_rework"
collector_state['active_competitors'].remove("ChatGPT")
collector_state['pending_rework'] = ["ChatGPT"]
collector_state['last_feedback'] = issue

save_agent_state(collector_state, 'agent-states/collector-agent-state.json')
save_agent_state(reviewer_state, 'agent-states/reviewer-agent-state.json')

# 3. 发出通知（可选）
print(f"Feedback issued to {issue['target_agent']}: {issue['issue']}")
```

**Collector 重新处理**：
```python
# Collector 启动后检查是否有待重做任务
collector_state = load_agent_state('agent-states/collector-agent-state.json')

if 'pending_rework' in collector_state and collector_state['pending_rework']:
    rework_competitors = collector_state['pending_rework']
    feedback = collector_state['last_feedback']
    
    print(f"Reworking {rework_competitors} due to: {feedback['issue']}")
    # 重新采集
    # ...
    
    # 完成后更新状态
    collector_state['pending_rework'] = []
    collector_state['active_competitors'].extend(rework_competitors)
    collector_state['rework_history'].append({
        "competitor": rework_competitors[0],
        "reason": feedback['issue'],
        "resolution": "Used Selenium to extract dynamic content",
        "timestamp": datetime.now().isoformat()
    })
    save_agent_state(collector_state, 'agent-states/collector-agent-state.json')
```

## 关键约定

### 时间戳约定
- 所有时间戳使用 **ISO 8601 格式**：`2026-05-22T14:30:45Z`
- 使用 UTC 时区（Z 表示 Zulu/UTC）

### 状态值约定
- `status` 字段值：`idle`, `running`, `blocked`, `error`, `completed`
- `enabled` 字段值：`true` / `false`
- 进度状态：`⏸ pending`, `⏳ in_progress`, `✓ completed`, `❌ failed`, `⚠️ partial`

### 文件更新原则
1. **频繁更新**：每个任务完成后立刻更新（不要等到 Agent 结束）
2. **原子操作**：每次更新是完整的，避免部分写入
3. **版本管理**：如果修改了状态文件结构，递增 `version` 字段
4. **日志保留**：不要删除 `recent_activities` 中的历史记录，只追加新记录

### 与 Git 的关系
- ✅ **应该 commit** 的：`claude-progress.txt`（全局进度）、`agent-states/` 中的里程碑快照
- ❌ **不应该 commit** 的：实时运行中频繁更新的状态（可用 `.gitignore` 排除 `agent-states/*.tmp.json`）
- 📝 **建议做法**：每周执行一次 `git add agent-states/` 来固定里程碑状态

## 最佳实践

1. **不要硬编码 Agent 名字**
   ```python
   # ❌ 不好
   state = json.load(open('agent-states/collector-agent-state.json'))
   
   # ✅ 好
   agent_name = 'collector-agent'
   state_file = f'agent-states/{agent_name}-state.json'
   state = json.load(open(state_file))
   ```

2. **定期备份重要的反馈信息**
   ```python
   # 在 claude-progress.txt 中记录反馈摘要
   with open('claude-progress.txt', 'a') as f:
       f.write(f"[{timestamp}] 质检反馈：{issue}\n")
   ```

3. **监控状态文件大小**
   - `recent_activities` 每个 Agent 保留最近 100 条
   - `feedback_issued` 保留完整历史（重要）

4. **定期同步到 claude-progress.txt**
   ```python
   # 每次有重要更新时
   update_global_progress(agent_state)
   ```

## 故障排查

### 问题：Agent 启动后不知道该做什么
**检查清单**：
1. `next_action` 字段是否明确？
2. `status` 是否是 `idle` 或 `blocked`？
3. 是否有 `pending_rework` 或 `review_queue`？

### 问题：反馈闭环卡住
**检查清单**：
1. Reviewer 的 `feedback_issued` 是否更新了？
2. Collector 的 `pending_rework` 字段是否同步？
3. `last_feedback` 中有没有记录反馈原因？

### 问题：无法追踪数据来源
**检查清单**：
1. 每条数据是否在 `feedback_issued` 中都有 `source_url`？
2. `recent_activities` 中是否记录了采集来源？

## 相关文档

- [claude-progress.txt](../claude-progress.txt) — 系统全局进度
- [docs/agent-protocol.md](./agent-protocol.md) — Agent 通信协议（待创建）
- [docs/git-conventions.md](./git-conventions.md) — Git 提交规范

---

**最后更新**: 2026-05-22
