"""LLM 真实返回值的形状容错回归测试。

背景：DeepSeek/OpenAI 调用成功并返回了真实数据，但后端解析层对形状要求过严，
校验失败后被宽泛 except 静默吞掉、退回硬编码模板，用户看到的报告全是占位符。
这些用例锁死真实日志里出现过的两种失配，防止回归。
"""

from agents.analyst import _coerce_mapping, _coerce_personas
from graph.state import StructuredCompetitorProfile
from services.llm.usage import (
    collected_degradations,
    record_degradation,
    reset_capture,
    start_capture,
)
from services.survey.tool import _safe_int


def test_coerce_personas_accepts_single_dict_from_llm() -> None:
    # 真实日志失配：user_personas 返回成 dict（schema 要 list[dict]）
    value = {"source_ids": ["src_tavily_1"], "label": "核心用户"}
    assert _coerce_personas(value) == [value]


def test_coerce_personas_unwraps_nested_list() -> None:
    value = {"personas": [{"label": "A"}, {"label": "B"}]}
    assert _coerce_personas(value) == [{"label": "A"}, {"label": "B"}]


def test_coerce_personas_filters_non_dict_items() -> None:
    assert _coerce_personas([{"label": "A"}, "junk", 3]) == [{"label": "A"}]


def test_coerce_personas_handles_garbage() -> None:
    assert _coerce_personas(None) == []
    assert _coerce_personas("nope") == []


def test_coerce_mapping_recovers_dict_from_list() -> None:
    assert _coerce_mapping([{"rows": []}]) == {"rows": []}
    assert _coerce_mapping({"rows": []}) == {"rows": []}
    assert _coerce_mapping("nope") == {}


def test_profile_builds_from_coerced_llm_shapes() -> None:
    # 这正是修复前 analyst 崩溃、退回模板的输入组合
    profile = StructuredCompetitorProfile(
        competitor_name="Trae",
        feature_tree=_coerce_mapping({"rows": []}),
        pricing=_coerce_mapping({"tiers": []}),
        user_personas=_coerce_personas({"source_ids": ["src_tavily_1"]}),
        swot=_coerce_mapping({"strengths": []}),
        source_ids=["src_tavily_1"],
    )
    assert profile.user_personas == [{"source_ids": ["src_tavily_1"]}]


def test_safe_int_survives_word_frequency() -> None:
    # 真实日志失配：frequency 返回成 'high'，旧代码 int('high') 直接崩
    assert _safe_int("high", default=5) == 3
    assert _safe_int("medium", default=5) == 2
    assert _safe_int("low", default=5) == 1
    assert _safe_int("unknown-word", default=5) == 5
    assert _safe_int("7", default=5) == 7
    assert _safe_int(4, default=5) == 4
    assert _safe_int(None, default=5) == 5
    assert _safe_int(True, default=5) == 5


def test_degradation_capture_roundtrip() -> None:
    token = start_capture()
    try:
        assert collected_degradations() == []
        record_degradation("analyst: ValidationError: boom")
        assert collected_degradations() == ["analyst: ValidationError: boom"]
    finally:
        reset_capture(token)
    # capture 关闭后不应泄漏
    assert collected_degradations() == []
