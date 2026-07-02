import type { DimensionSpec, TaskScopeContract } from "./types";
import { CORE_DIMENSION_IDS, emptyUserResearchPlan } from "./types";

/**
 * The 4 locked core dimensions that every task must include.
 * Titles and intents here are defaults — the AI may rewrite the intent
 * to better fit the user's brief; the user can edit either.
 */
export function buildCoreDimensions(): DimensionSpec[] {
  return [
    {
      id: CORE_DIMENSION_IDS.FEATURE_TREE,
      layer: "core",
      source: "system",
      title: "功能树",
      title_i18n: { zh: "功能树", en: "Feature Tree" },
      intent: "对比各竞品的核心产品线、功能矩阵与差异化能力",
      intent_i18n: {
        zh: "对比各竞品的核心产品线、功能矩阵与差异化能力",
        en: "Compare core product lines, feature matrices, and differentiators across competitors",
      },
      schema_ref: "FeatureTree",
      enabled: true,
      locked: true,
      order: 0,
    },
    {
      id: CORE_DIMENSION_IDS.PRICING_MODEL,
      layer: "core",
      source: "system",
      title: "定价模型",
      title_i18n: { zh: "定价模型", en: "Pricing Model" },
      intent: "梳理各 SKU 价格区间、套装策略、会员折扣与大促节奏",
      intent_i18n: {
        zh: "梳理各 SKU 价格区间、套装策略、会员折扣与大促节奏",
        en: "Map SKU price tiers, bundle strategy, member discounts, and promotional cadence",
      },
      schema_ref: "PricingModel",
      enabled: true,
      locked: true,
      order: 1,
    },
    {
      id: CORE_DIMENSION_IDS.USER_PERSONA,
      layer: "core",
      source: "system",
      title: "用户画像",
      title_i18n: { zh: "用户画像", en: "User Persona" },
      intent: "从电商评论与官方文案中归纳目标用户群与典型痛点",
      intent_i18n: {
        zh: "从电商评论与官方文案中归纳目标用户群与典型痛点",
        en: "Derive target audience segments and pain points from e-commerce reviews and brand copy",
      },
      schema_ref: "UserPersona",
      enabled: true,
      locked: true,
      order: 2,
    },
    {
      id: CORE_DIMENSION_IDS.SWOT,
      layer: "core",
      source: "system",
      title: "SWOT",
      title_i18n: { zh: "SWOT", en: "SWOT" },
      intent: "结合上述维度产出每家竞品的优劣势、机会与威胁分析",
      intent_i18n: {
        zh: "结合上述维度产出每家竞品的优劣势、机会与威胁分析",
        en: "Synthesize strengths, weaknesses, opportunities, and threats for each competitor using the dimensions above",
      },
      schema_ref: "SWOT",
      enabled: true,
      locked: true,
      order: 3,
    },
  ];
}

/**
 * Domain-agnostic empty draft for the real `/tasks/new/scoping` path while
 * ScopingAgent is not yet wired up. 4 locked core dimensions, zero extensions,
 * zero competitors — the user fills in the rest by hand.
 *
 * Per PRD §十一-quater 11Q.7, the real path MUST use this (or the real
 * ScopingAgent output) and MUST NOT fall back to any domain-bound mock.
 */
export function buildEmptyDraftContract(userBrief: string): TaskScopeContract {
  return {
    task_id: `task_${Date.now()}`,
    target_product: null,
    competitors: [],
    user_brief: userBrief,
    clarifications: [],
    dimensions: buildCoreDimensions(),
    user_research_plan: emptyUserResearchPlan(),
    frozen_at: null,
  };
}
