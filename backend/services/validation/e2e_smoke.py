from time import perf_counter
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.report import ReportMetrics
from schemas.scope import (
    CompetitorCandidate,
    ScopeDimension,
    TaskScopeContract,
    UserResearchPlan,
)
from services.exporter import export_markdown, export_pdf, export_pptx
from services.runs.manager import RunManager


class SmokeCaseResult(BaseModel):
    case_id: str
    task_id: UUID
    run_id: UUID
    status: str
    elapsed_seconds: float
    report_ready: bool
    claim_count: int
    source_count: int
    survey_result_count: int
    timeline_event_count: int
    survey_stage_count: int
    retry_count: int = 0
    feedback_loop_detected: bool = False
    recovery_source_count: int = 0
    metrics: ReportMetrics | None = None
    export_checks: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SmokeRunResult(BaseModel):
    mode: str
    case_count: int
    passed: bool
    cases: list[SmokeCaseResult]


async def run_backend_smoke_suite(
    run_manager: RunManager,
    *,
    force_feedback_demo: bool = False,
) -> SmokeRunResult:
    cases: list[SmokeCaseResult] = []
    for scope in _smoke_scopes():
        cases.append(
            await _run_case(
                run_manager,
                scope,
                force_feedback_demo=force_feedback_demo,
            )
        )
    return SmokeRunResult(
        mode="mock_or_configured_real_path",
        case_count=len(cases),
        passed=all(case.report_ready and not case.warnings for case in cases),
        cases=cases,
    )


async def _run_case(
    run_manager: RunManager,
    scope_contract: TaskScopeContract,
    *,
    force_feedback_demo: bool,
) -> SmokeCaseResult:
    started = perf_counter()
    record = await run_manager.start_run(scope_contract)
    state = run_manager.build_initial_state(
        record,
        scope_contract,
        force_feedback_demo=force_feedback_demo,
    )
    await run_manager.execute_run(record.id, state)

    report = await run_manager.get_report(scope_contract.id)
    timeline = await run_manager.get_timeline(record.id)
    warnings: list[str] = []
    export_checks: dict[str, int] = {}
    metrics: ReportMetrics | None = None
    claim_count = 0
    source_count = 0
    survey_result_count = 0
    recovery_source_count = 0

    if report is None:
        warnings.append("report_not_ready")
    else:
        metrics = report.metrics
        claim_count = len(report.claims)
        source_count = len(report.sources)
        recovery_source_count = sum(
            1 for source in report.sources if source.provider == "feedback_recovery"
        )
        survey_result_count = len(report.structured_content.get("survey") or [])
        if not report.claims:
            warnings.append("no_claims")
        if any(not claim.source_ids for claim in report.claims):
            warnings.append("claim_without_source_ids")
        if not report.structured_content.get("survey"):
            warnings.append("missing_survey_section")
        export_checks = {
            "markdown_bytes": len(export_markdown(report)),
            "pdf_bytes": len(export_pdf(report)),
            "pptx_bytes": len(export_pptx(report)),
        }
        if export_checks["pdf_bytes"] == 0 or export_checks["pptx_bytes"] == 0:
            warnings.append("empty_export")

    survey_stage_count = sum(1 for trace in timeline if trace.agent_name == "SurveyTool")
    if survey_stage_count < 7:
        warnings.append("missing_survey_stage_traces")
    feedback_loop_detected = record.retry_count > 0 and recovery_source_count > 0
    if force_feedback_demo and not feedback_loop_detected:
        warnings.append("feedback_loop_not_detected")

    return SmokeCaseResult(
        case_id=_case_id(scope_contract),
        task_id=scope_contract.id,
        run_id=record.id,
        status=record.status,
        elapsed_seconds=round(perf_counter() - started, 4),
        report_ready=report is not None,
        claim_count=claim_count,
        source_count=source_count,
        survey_result_count=survey_result_count,
        timeline_event_count=len(timeline),
        survey_stage_count=survey_stage_count,
        retry_count=record.retry_count,
        feedback_loop_detected=feedback_loop_detected,
        recovery_source_count=recovery_source_count,
        metrics=metrics,
        export_checks=export_checks,
        warnings=warnings,
    )


def _smoke_scopes() -> list[TaskScopeContract]:
    return [
        _scope(
            "saas_collaboration",
            "分析 Notion、Lark、Airtable 的协作能力、定价和用户声音。",
            ["Notion", "Lark", "Airtable"],
        ),
        _scope(
            "ai_assistants",
            "分析 ChatGPT、Claude、Gemini 在企业知识工作场景中的差异。",
            ["ChatGPT", "Claude", "Gemini"],
        ),
        _scope(
            "short_video_platforms",
            "分析 抖音、快手、小红书 的内容生态、商业化和用户痛点。",
            ["抖音", "快手", "小红书"],
        ),
    ]


def _scope(case_id: str, user_brief: str, competitors: list[str]) -> TaskScopeContract:
    return TaskScopeContract(
        user_brief=user_brief,
        intent_mode="list",
        competitors=[
            CompetitorCandidate(
                name=name,
                source="nl_extracted",
                rationale=f"{case_id} smoke case",
            )
            for name in competitors
        ],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="功能树",
                intent="梳理核心能力、差异化功能和功能覆盖。",
                layer="core",
                order=1,
                locked=True,
                schema_ref="FeatureTree",
            ),
            ScopeDimension(
                id="core.pricing",
                title="定价模型",
                intent="比较价格层级、套餐结构和付费门槛。",
                layer="core",
                order=2,
                locked=True,
                schema_ref="PricingModel",
            ),
            ScopeDimension(
                id="core.persona",
                title="用户画像",
                intent="识别目标用户、使用场景和典型痛点。",
                layer="core",
                order=3,
                locked=True,
                schema_ref="UserPersona",
            ),
            ScopeDimension(
                id="core.swot",
                title="SWOT",
                intent="总结优势、劣势、机会和威胁。",
                layer="core",
                order=4,
                locked=True,
                schema_ref="SWOT",
            ),
            ScopeDimension(
                id="ext.user_voice",
                title="用户声音",
                intent="聚合公开评论、调研报告和问卷/访谈信号。",
                layer="extension",
                order=5,
                source="ai_suggested",
            ),
        ],
        user_research_plan=UserResearchPlan(enabled=True),
    )


def _case_id(scope_contract: TaskScopeContract) -> str:
    names = "-".join(competitor.name for competitor in scope_contract.competitors)
    return names.lower().replace(" ", "_")
