def language_instruction(language: str) -> str:
    """统一的语言归一指令，供 Analyst 抽取与 Writer 成文共用。

    采集刻意保持多语言（很多 dev-tool 的定价/文档只有英文），否则会丢失权威来源；
    因此 LLM 默认会回显源语言。本指令强制把人读文本翻成目标语言，而产品/品牌/套餐名
    与数字保持原文不译，source_ids 逐字复制。
    """
    label = "简体中文 (Simplified Chinese)" if language == "zh" else language
    return (
        f" Write all human-readable text (narrative paragraphs, section intros, feature "
        f"names, descriptions, notes, pricing tiers and highlights, persona labels/needs/"
        f"pain points, SWOT text, summaries, headings, and bullets) in {label}. Do not "
        f"echo source-language (e.g. English) sentences — translate them into {label}. "
        f"Keep product and brand names, plan/tier names, and numbers with their units "
        f"verbatim. source_ids must still be copied verbatim from the provided sources."
    )
