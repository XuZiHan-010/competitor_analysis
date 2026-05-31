"use client";

import { useLangStore, type Lang } from "@/stores/lang-store";

export const translations = {
  zh: {
    navReports: "我的报告",
    pageTitle: "Strata — 竞品分析情报系统",
    pageDescription:
      "多 Agent 协作的结构化竞品分析平台。从需求描述到可溯源报告，全自动产出。",
    navAccount: "账户",
    navDemo: "30秒demo演示",
    switchToEnglish: "Switch to English",
    switchToChinese: "切换到中文",
    themeToggle: "主题切换",
    switchTheme: "切换到{mode}色模式",
    lightMode: "浅",
    darkMode: "深",
    stageStatus: "Stage 2 · 施工中",
    stageBackDefault: "回到任务创建",
    loginTitle: "登录",
    loginBlurb:
      "邮箱验证码登录页。Stage 2 接入 /api/auth/send-code 与 /api/auth/verify 两个端点；JWT 落 httpOnly cookie。",
    loginBack: "先体验 demo",
    reportsTitle: "我的报告",
    reportsBlurb:
      "历史任务列表页。Stage 2 将以编辑式索引卡列出每份报告：任务名、创建时间、竞品数、状态、报告摘要，点击进入报告或重跑任务。",
    runTitle: "DAG 实时可视化",
    runBlurb:
      "任务运行页。Stage 2 将在这里渲染 4 Agent 的实时进度、节点状态、Trace 日志、以及反馈闭环触发情况。数据源走 SSE 长连接，配合 React Flow 做拓扑展示。",
    reportTitle: "竞品分析报告",
    reportBlurb:
      "报告查看页。Stage 2 将按 TaskScopeContract 的章节顺序动态渲染：核心 4 章走固定模板，扩展章节渲染 ExtensionFinding。每条结论旁有溯源图标，点开侧滑面板看原文片段与 URL。语言切换会同步请求后端生成对应语言版本，并保留 source_ids。",
    taskHeadline: "多 Agent 竞品情报平台",
    taskIntro:
      "描述你的竞品分析需求。默认情况下，Strata 会先生成研究大纲供你确认；如果需求已经足够明确，或你明确要求直接生成报告，Strata 将跳过大纲直接开始分析。",
    taskPlaceholder:
      "例：对比 SK-II、资生堂、雅诗兰黛在中国电商渠道的会员体系与 KOL 投放策略…",
    charUnit: "字",
    fillExample: "填入示例：{label}",
    analyzeNow: "直接分析",
    generatePlan: "生成研究计划",
    rewriteBrief: "重写需求",
    scopingStatus: "Scoping / 立项中",
    scopingTitle: "确定分析维度",
    scopingLoading: "Scoping Agent 正在分析需求",
    scopingIntroBefore: "AI 已根据需求拟了一份大纲：",
    scopingCore: "项核心",
    scopingMiddle: "维度（不可删除）加",
    scopingExtension: "项扩展",
    scopingIntroAfter: "维度。你可以编辑标题、改意图、增删扩展项、调整顺序。",
    outlineTitle: "本次分析大纲",
    enabled: "启用",
    outlineTip: "拖拽 ⋮ 调整顺序 · 点标题或意图直接编辑 · 取消勾选 = 本次不输出",
    confirmAnalysis: "确认 · 开始分析",
    taskCreated: "任务已创建",
    taskCreatedDescription: "Stage 2 接入 DAG 页后会跳到运行页",
    recommendedCompetitors: "AI 推荐竞品",
    removeCompetitor: "移除 {name}",
    competitorPlaceholder: "名称后 Enter…",
    competitorInputLabel: "新增竞品名称",
    addCompetitorLabel: "添加竞品",
    add: "添加",
    addDimension: "增加自定义维度",
    newDimensionTitle: "新增分析维度",
    newDimensionDescription:
      "添加一个不在 AI 推荐列表里的扩展章节。AI 会基于你写的意图描述去采集和分析这一节内容。",
    sectionTitle: "章节标题",
    requiredMark: "*",
    sectionTitlePlaceholder: "例：可持续包装策略",
    intentLabel: "意图描述",
    optionalIntentHint: "可选 · 帮 AI 知道这章重点抽什么",
    intentPlaceholder: "例：包材碳足迹声明、可回收/可补充装比例、品牌承诺…",
    cancel: "取消",
    disableOrEnableDimension: "{action}启用 {title}",
    cancelAction: "取消",
    coreDimension: "核心维度",
    coreDimensionTooltip: "核心维度 · 比赛要求保留",
    extensionDimension: "扩展维度",
    extensionDimensionTooltip: "扩展维度 · 按本次任务定制",
    editSectionTitle: "编辑章节标题",
    editTitleWithName: "编辑标题：{title}",
    editIntentDescription: "编辑章节意图描述",
    intentInlinePlaceholder: "一句话描述这章重点关注什么…",
    editIntent: "编辑章节意图",
    addIntentDescription: "添加意图描述…",
    dragToSort: "拖拽排序",
    coreCannotDelete: "核心章节不可删除",
    deleteDimension: "删除 {title}",
    reguidePlaceholder: "换需求、补维度、改重点都行：例，加入会员等级与积分体系的对比",
    reguideAria: "向 AI 提供补充指导，重新生成大纲",
    reguideLabel: "重新指导 · Re-brief",
    regenerating: "重新生成中",
    applyReguide: "应用并重新生成",
    reguideSuccess: "已根据新指导重新生成",
    reguideSuccessDescription: "之前对章节的人工编辑会被覆盖",
    navReportSearch: "报告检索",
    searchTitle: "报告检索",
    searchPlaceholder: "搜索历史报告：竞品、功能、定价、用户声音…",
    searchIdle: "输入关键词，跨所有历史报告做语义检索",
    searchEmpty: "没有匹配的报告，换个说法再试",
    searchError: "检索失败，请稍后重试",
    searchModePgvector: "语义检索",
    searchModeKeyword: "关键词匹配",
    reportLangLabel: "报告语言",
    reportLangError: "语言切换失败，请重试",
    navSettings: "设置",
    settingsDataSourceTitle: "数据源管理",
    settingsDataSourceIntro:
      "竞品分析可检索的数据源。本系统已生成的报告进入语义库，可在「报告检索」中跨报告语义召回。",
    settingsStatusEnabled: "已启用",
    settingsStatusRoadmap: "路线图",
    settingsHistoryTitle: "历史报告语义库",
    settingsHistoryDesc:
      "系统已生成并可溯源的报告（reports / claims / sources）写入 pgvector 向量库，支持跨报告语义检索。",
    settingsHistoryMeta: "数据范围 · 本系统自产报告",
    settingsKbTitle: "企业知识库 / 文档 RAG",
    settingsKbDesc:
      "接入 Confluence / SharePoint / 付费数据库 / 内部销售数据等异构知识源，作为分析的外部证据。",
    settingsKbMeta: "本期不实现 · 见 PRD §十一-ter 生产化路线图",
    settingsRoadmapNote: "本页为数据源能力的只读概览，路线图项不提供上传 / 连接操作。",
  },
  en: {
    navReports: "My Reports",
    pageTitle: "Strata — Competitive Intelligence System",
    pageDescription:
      "A structured competitive intelligence platform powered by multi-agent collaboration, from raw brief to traceable report.",
    navAccount: "Account",
    navDemo: "30s demo",
    switchToEnglish: "Switch to English",
    switchToChinese: "Switch to Chinese",
    themeToggle: "Theme toggle",
    switchTheme: "Switch to {mode} mode",
    lightMode: "light",
    darkMode: "dark",
    stageStatus: "Stage 2 · In progress",
    stageBackDefault: "Back to task setup",
    loginTitle: "Log In",
    loginBlurb:
      "Email verification login page. Stage 2 will connect /api/auth/send-code and /api/auth/verify, then store JWT in an httpOnly cookie.",
    loginBack: "Try the demo first",
    reportsTitle: "My Reports",
    reportsBlurb:
      "Historical task index. Stage 2 will show each report as an editorial card with task name, creation time, competitor count, status, summary, and entry points for viewing or rerunning.",
    runTitle: "Live DAG View",
    runBlurb:
      "Task run page. Stage 2 will render the four Agent nodes, live progress, node state, Trace logs, and feedback-loop events over SSE with a React Flow topology.",
    reportTitle: "Competitive Analysis Report",
    reportBlurb:
      "Report viewer. Stage 2 will render chapters in TaskScopeContract order: four core templates plus ExtensionFinding sections. Each claim keeps a provenance action that opens original snippets and URLs. Language switching will request the backend language version while preserving source_ids.",
    taskHeadline: "Multi-Agent Competitive Intelligence",
    taskIntro:
      "Describe your competitive analysis request. By default, Strata will generate a research outline for review first; if your request is specific enough, or you ask for a direct report, Strata will skip the outline and begin analysis.",
    taskPlaceholder:
      "e.g. Compare SK-II, Shiseido, and Estée Lauder on membership programs and KOL strategy in Chinese e-commerce…",
    charUnit: "chars",
    fillExample: "Use example: {label}",
    analyzeNow: "Analyze Now",
    generatePlan: "Generate Research Plan",
    rewriteBrief: "Rewrite brief",
    scopingStatus: "Scoping / Drafting",
    scopingTitle: "Confirm Analysis Dimensions",
    scopingLoading: "Scoping Agent is analyzing the brief",
    scopingIntroBefore: "AI drafted an outline with",
    scopingCore: "core",
    scopingMiddle: "dimensions, plus",
    scopingExtension: "extension",
    scopingIntroAfter:
      "dimensions. You can edit titles, refine intent, add or remove extensions, and reorder the outline.",
    outlineTitle: "Analysis Outline",
    enabled: "enabled",
    outlineTip:
      "Drag ⋮ to reorder · click title or intent to edit · unchecked dimensions will be excluded",
    confirmAnalysis: "Confirm · Start Analysis",
    taskCreated: "Task created",
    taskCreatedDescription: "Stage 2 will route to the DAG run page once connected",
    recommendedCompetitors: "AI recommended competitors",
    removeCompetitor: "Remove {name}",
    competitorPlaceholder: "Enter after name…",
    competitorInputLabel: "New competitor name",
    addCompetitorLabel: "Add competitor",
    add: "Add",
    addDimension: "Add custom dimension",
    newDimensionTitle: "New Analysis Dimension",
    newDimensionDescription:
      "Add an extension section outside the AI recommendations. The agent will use your intent description to collect and analyze that chapter.",
    sectionTitle: "Section title",
    requiredMark: "*",
    sectionTitlePlaceholder: "e.g. Sustainable packaging strategy",
    intentLabel: "Intent",
    optionalIntentHint: "Optional · tell AI what this section should extract",
    intentPlaceholder:
      "e.g. carbon footprint claims, recyclable or refillable packaging share, brand commitments…",
    cancel: "Cancel",
    disableOrEnableDimension: "{action}enable {title}",
    cancelAction: "Disable ",
    coreDimension: "Core dimension",
    coreDimensionTooltip: "Core dimension · required by the competition brief",
    extensionDimension: "Extension dimension",
    extensionDimensionTooltip: "Extension dimension · customized for this task",
    editSectionTitle: "Edit section title",
    editTitleWithName: "Edit title: {title}",
    editIntentDescription: "Edit section intent",
    intentInlinePlaceholder: "Describe what this section should focus on…",
    editIntent: "Edit section intent",
    addIntentDescription: "Add intent description…",
    dragToSort: "Drag to reorder",
    coreCannotDelete: "Core sections cannot be deleted",
    deleteDimension: "Delete {title}",
    reguidePlaceholder:
      "Change the brief, add dimensions, or shift focus: e.g. include membership tiers and points programs",
    reguideAria: "Give AI additional guidance and regenerate the outline",
    reguideLabel: "Re-brief",
    regenerating: "Regenerating",
    applyReguide: "Apply and regenerate",
    reguideSuccess: "Regenerated with the new guidance",
    reguideSuccessDescription: "Previous manual edits to sections were overwritten",
    navReportSearch: "Search Reports",
    searchTitle: "Search Reports",
    searchPlaceholder: "Search past reports: competitors, features, pricing, user voice…",
    searchIdle: "Type a query to semantically search across all past reports",
    searchEmpty: "No matching reports — try rephrasing",
    searchError: "Search failed, please try again",
    searchModePgvector: "Semantic",
    searchModeKeyword: "Keyword",
    reportLangLabel: "Report language",
    reportLangError: "Language switch failed, please retry",
    navSettings: "Settings",
    settingsDataSourceTitle: "Data Sources",
    settingsDataSourceIntro:
      "Sources the analysis can retrieve from. Reports this system has generated enter the semantic library and are recallable across reports in Search Reports.",
    settingsStatusEnabled: "Enabled",
    settingsStatusRoadmap: "Roadmap",
    settingsHistoryTitle: "Historical Report Semantic Library",
    settingsHistoryDesc:
      "Generated, traceable reports (reports / claims / sources) are written to a pgvector store, enabling semantic search across past reports.",
    settingsHistoryMeta: "Scope · self-produced reports",
    settingsKbTitle: "Enterprise Knowledge Base / Document RAG",
    settingsKbDesc:
      "Connect heterogeneous sources like Confluence / SharePoint / paid databases / internal sales data as external evidence for analysis.",
    settingsKbMeta: "Not in this release · see PRD §11-ter production roadmap",
    settingsRoadmapNote:
      "This page is a read-only overview of data-source capabilities; roadmap items expose no upload / connect actions.",
  },
} as const;

export type TranslationKey = keyof typeof translations.zh;

export function useI18n() {
  const lang = useLangStore((s) => s.lang);

  function t(key: TranslationKey, values?: Record<string, string | number>) {
    let text: string = translations[lang][key];
    if (!values) return text;
    for (const [name, value] of Object.entries(values)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
    return text;
  }

  return { lang, t };
}

export function htmlLang(lang: Lang) {
  return lang === "zh" ? "zh-CN" : "en";
}
