# CLAUDE.md — frontend (前端)

> 作用域：**本文件只在 Claude 读 `frontend/` 下的文件时加载**。
> 根 [AGENTS.md](../AGENTS.md) 的所有规则仍然适用；本文件只补本目录专属的约束。

---

## 🔴 命令：改这块代码 = 只跑这块的命令

**核心原则**：改了 `frontend/` 里的文件后，**只跑本目录的 lint / typecheck / test**，不要回项目根跑「整个 monorepo」的任何命令。后端在 [backend/](../backend/) 是另一套工具链（Python / ruff / pytest），混跑浪费几十分钟且烧 context。

### 必须在 `frontend/` 目录下执行

| 操作 | 命令 | 何时跑 |
|---|---|---|
| Lint | `npm run lint` | 改完代码、commit 前、push 前 |
| 类型检查 | `npm run typecheck` | 改了 type/interface 或跨文件 import 后 |
| dev server | `npm run dev` | 验证 UI 行为时 |
| 生产构建 | `npm run build` | 大改前后；CI 会跑（一次完整构建 ~30-60s） |

**禁止做的事**：
- ❌ 在项目根跑 `npm` / `pnpm` 任何命令（项目根没有 package.json）
- ❌ 改前端文件后跑后端的 `pytest` / `ruff`（无关）
- ❌ 跑「整个项目」的测试套件（不存在这种东西；monorepo 各目录独立）

### 测试现状

⚠️ **`frontend/` 目前没有自动化测试**（`package.json` 里没有 `test` script）。

改动验证流程：
1. `npm run lint` 0 error
2. `npx tsc --noEmit` 0 error
3. `npm run dev` 起 dev server，**肉眼验证关键页面**：`/tasks/new` → `/tasks/new/scoping`
4. 主要交互必走一遍：拖拽维度排序 / 编辑标题与意图 / 增删扩展维度 / 主题切换 / 多语言切换

未来加 Vitest / Playwright 后，在本文件更新命令表。

---

## 设计 / 重构必走 skill（与 AGENTS.md §五 7 呼应）

任何前端组件、页面、UI 设计或重构任务**开工前必须先调用**：
- `frontend-design` —— 生成有设计感的代码、避免 generic AI 风格
- `web-design-guidelines` —— 按 Vercel Web Interface Guidelines 做 a11y / 可用性 / typography 合规审查

按需挑选，不要跳过。

---

## 技术栈约束

| 项 | 约定 |
|---|---|
| 包管理器 | **npm**（有 `package-lock.json`）。不要换成 pnpm / yarn，会破坏 lock |
| TypeScript | `strict: true`，**不允许 `any`**，用 `unknown` + 类型守卫 |
| 组件 | 函数式 + hooks，不写 class component |
| Server / Client | Next.js App Router 默认 server component；只在需要 hook / event handler 时加 `"use client"` |
| 状态管理 | **Zustand**（store 放 `src/stores/`），不引入 Redux / Jotai |
| 样式 | Tailwind v4 + shadcn/ui base 组件（在 `src/components/ui/`），不要写独立 .module.css |
| 路径别名 | `@/` → `src/`（tsconfig 已配），不要用相对路径 `../../../` |
| 动画 | 全局 `prefers-reduced-motion` 已在 `globals.css` 兜底；新增动画用 `transform` / `opacity` |
| 国际化 | 用项目自实现的 `lang-store`，不引入 next-intl / i18next |

---

## 目录约定

```
frontend/src/
├── app/                Next.js App Router 页面（含 layout / globals.css）
├── components/
│   ├── ui/             shadcn/ui base 组件（不要手改，重新生成）
│   ├── layout/         布局类组件（导航 / 主题切换 / 容器）
│   └── scoping/        Stage 1 立项页专属组件
├── lib/
│   ├── mocks/          Stage 1/2 用的 mock 数据 + delay 工具
│   └── utils.ts        cn() 等通用工具
└── stores/             Zustand store
```

新增功能时，组件按 **功能域** 分目录（如 `components/dag/` 给 Stage 2 的 DAG 可视化用），不要按"组件类型"分（如 `components/buttons/` 这种反模式）。
