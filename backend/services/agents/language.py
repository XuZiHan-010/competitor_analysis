def language_instruction(language: str) -> str:
    """统一的语言归一指令，供 Analyst 抽取与 Writer 成文共用。

    采集刻意保持多语言（很多 dev-tool 的定价/文档只有英文），否则会丢失权威来源；
    因此 LLM 默认会回显源语言。本指令强制把人读文本翻成目标语言，而产品/品牌/套餐名
    与数字保持原文不译，source_ids 逐字复制。
    """
    label = "简体中文 (Simplified Chinese)" if language == "zh" else language
    return (
        f" 所有面向读者的文本，包括叙事段落、章节导语、功能名称、描述、备注、"
        f"定价档位及其亮点、用户画像标签、需求与痛点、SWOT 文本、摘要、标题和"
        f"项目符号，都必须使用 {label}。字段映射为 feature names=功能名称、"
        f"pricing tiers=定价档位。不得直接回显来源语言的句子，例如英文原句；"
        f"必须翻译为 {label}（translation_mode=translate）。产品名、品牌名、套餐或"
        f"档位名称、数字及其单位采用 verbatim 规则逐字保留；source_ids 也必须从所提供"
        f"来源中逐字复制。"
    )
