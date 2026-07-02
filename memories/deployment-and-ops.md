---
name: deployment-and-ops
description: Railway 上线、外部服务和运行排障的长期记忆
type: reference
---

# Deployment And Ops

## 线上组件

本项目线上由几类服务组成：

- Railway 前端服务：Next.js。
- Railway 后端服务：FastAPI Dockerfile。
- Neon：Postgres 与 pgvector。
- Upstash：Redis，用于生产事件流。
- OpenAI / DeepSeek：按 Agent 分配模型能力。
- Tavily / DuckDuckGo / SerpApi：分层搜索与兜底。
- LangSmith：开发期 debug 和答辩展示增强层。

## 安全边界

- 真实密钥、凭据和服务地址只放在平台变量或本地环境文件中。
- memory、docs、plan、PR 描述和截图中都不能写真实敏感值。
- 示例环境文件只放变量名示例，不放真实值。
- LangSmith 是增强可观测层，不能替代报告溯源。

## 常见排障方向

- 前端请求失败：先看 API base、CORS、Railway 前端变量和浏览器网络面板。
- 后端启动失败：看 Railway 构建日志、运行日志、迁移日志和健康检查。
- 数据库问题：看迁移、连接配置、Repository 层异常。
- Redis 事件流问题：看 StreamBridge、TTL、maxlen、SSE 订阅。
- Agent 卡住：看 RunManager、workflow deadline、LLM 调用超时和 trace。
- 报告空内容：从 Collector 来源、Analyst 结构化、QA issue、Writer field gaps 逐层排查。

## 验证入口

上线后最小验证：

1. 后端健康检查。
2. 前端打开任务创建页。
3. 跑一条真实或 demo 主路径。
4. 检查报告页、溯源、导出和任务 timeline。

最新部署步骤以 [docs/deployment.md](../docs/deployment.md) 为准。
