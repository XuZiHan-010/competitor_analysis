import type {
  ClarifyingQuestion,
  DimensionSpec,
  TaskScopeContract,
} from "./types";
import { CORE_DIMENSION_IDS } from "./types";

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
      intent: "对比各竞品的核心产品线、功能矩阵与差异化能力",
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
      intent: "梳理各 SKU 价格区间、套装策略、会员折扣与大促节奏",
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
      intent: "从电商评论与官方文案中归纳目标用户群与典型痛点",
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
      intent: "结合上述维度产出每家竞品的优劣势、机会与威胁分析",
      schema_ref: "SWOT",
      enabled: true,
      locked: true,
      order: 3,
    },
  ];
}

/**
 * The 3 extension dimensions our pretend Scoping Agent inferred from the
 * user's brief about high-end skincare brands.
 */
export function buildSkincareExtensions(): DimensionSpec[] {
  return [
    {
      id: "ext.membership_promo",
      layer: "extension",
      source: "ai_suggested",
      title: "会员体系与折扣节奏",
      intent: "电商旗舰店黑卡 / 积分 / 双11 与 618 大促力度对比",
      schema_ref: null,
      enabled: true,
      locked: false,
      order: 4,
    },
    {
      id: "ext.kol_endorsement",
      layer: "extension",
      source: "ai_suggested",
      title: "KOL 与代言矩阵",
      intent: "品牌代言人、头部主播合作、内容投放渠道与频次",
      schema_ref: null,
      enabled: true,
      locked: false,
      order: 5,
    },
    {
      id: "ext.channel_distribution",
      layer: "extension",
      source: "ai_suggested",
      title: "渠道与铺货",
      intent: "线下专柜密度、电商旗舰店运营、免税与海淘渠道占比",
      schema_ref: null,
      enabled: true,
      locked: false,
      order: 6,
    },
  ];
}

/**
 * Clarifying questions surfaced by the Scoping Agent.
 *
 * Currently empty — the previous two mock questions (audience / history range)
 * were removed because they had no real effect on outline generation and the
 * UI section felt like decorative ceremony. Stage 2's real AI may produce
 * genuinely outline-shaping questions; when that happens, return them here and
 * the `<ClarifyingQuestions />` UI will reappear automatically.
 */
export function buildClarifyingQuestions(): ClarifyingQuestion[] {
  return [];
}

/**
 * The whole mock scope contract — what the Scoping Agent "returns"
 * after the user submits the brief about high-end skincare brands.
 */
export function buildSkincareMockContract(
  userBrief: string,
  competitors: string[],
): TaskScopeContract {
  return {
    task_id: `task_${Date.now()}`,
    target_product: null,
    competitors,
    user_brief: userBrief,
    clarifications: buildClarifyingQuestions(),
    dimensions: [...buildCoreDimensions(), ...buildSkincareExtensions()],
    frozen_at: null,
  };
}

/**
 * Heuristic competitor extraction from a freeform Chinese brief.
 * Looks for known high-end skincare brand names. In Stage 2 this is
 * replaced by the real LLM extraction; here it's just for demo realism.
 */
const KNOWN_BRANDS = [
  "SK-II",
  "SK2",
  "雅诗兰黛",
  "Estée Lauder",
  "资生堂",
  "Shiseido",
  "兰蔻",
  "Lancôme",
  "海蓝之谜",
  "La Mer",
  "赫莲娜",
  "HR",
  "黑绷带",
  "Helena Rubinstein",
];

export function extractCompetitorsFromBrief(brief: string): string[] {
  const found = new Set<string>();
  for (const brand of KNOWN_BRANDS) {
    if (brief.includes(brand)) found.add(normalizeBrand(brand));
  }
  return Array.from(found);
}

function normalizeBrand(b: string): string {
  if (b === "SK2") return "SK-II";
  if (b === "Estée Lauder") return "雅诗兰黛";
  if (b === "Shiseido") return "资生堂";
  if (b === "Lancôme") return "兰蔻";
  if (b === "La Mer") return "海蓝之谜";
  if (b === "HR" || b === "Helena Rubinstein") return "赫莲娜";
  return b;
}

/** Default placeholder brief shown in the textarea. */
export const DEFAULT_BRIEF_PLACEHOLDER =
  "例：帮我对比 SK-II、资生堂、雅诗兰黛 三个高端护肤品牌在中国电商的会员体系和 KOL 策略上的差异，重点关注 25-35 岁城市女性消费群体。";
