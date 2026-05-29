from uuid import UUID

from graph.state import WorkflowState
from schemas.report import Report, ReportClaim
from services.agents.decorators import traced_node
from services.llm import LLMClient
from services.metrics import calculate_report_metrics
from settings import get_settings


class WriterAgent:
    @traced_node(
        agent_name="WriterAgent",
        node_name="run_writer",
        prompt="Render a structured report with citations and multilingual-ready claims.",
    )
    async def run(
        self,
        state: WorkflowState,
        *,
        trace_context: object | None = None,
        language: str = "zh",
    ) -> Report:
        settings = get_settings()
        llm = LLMClient(settings)
        if llm.enabled and settings.deepseek_api_key:
            try:
                return await self._run_llm(state, llm, language=language)
            except Exception:
                pass
        return self._run_fallback(state, language=language)

    async def _run_llm(self, state: WorkflowState, llm: LLMClient, *, language: str) -> Report:
        settings = get_settings()
        sources = [s for result in state.raw_collections.values() for s in result.sources]
        source_ids_by_profile = {
            name: profile.source_ids for name, profile in state.structured_profiles.items()
        }
        profiles_payload = [p.model_dump(mode="json") for p in state.structured_profiles.values()]
        dims_payload = [d.model_dump() for d in state.scope_contract.dimensions if d.enabled]
        simulated_warnings = _build_simulated_warnings(state)

        payload = await llm.complete_json(
            provider="deepseek",
            model=settings.writer_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are WriterAgent. Return JSON with summary, sections, claims. "
                        "Render sections in the order of scope_contract dimensions. "
                        "Every claim must include source_ids from the provided profiles. "
                        "For any survey insight backed only by AI-simulated evidence, "
                        "prefix the text with '⚠️ [AI模拟] '."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Dimensions (ordered): {dims_payload}\n"
                        f"Profiles: {profiles_payload}\n"
                        f"Allowed source ids: {source_ids_by_profile}\n"
                        f"AI-simulated survey sections requiring ⚠️: {simulated_warnings}"
                    ),
                },
            ],
        )
        claims = self._claims_from_payload(payload, state)
        structured_content = {
            "summary": payload.get("summary", ""),
            "sections": payload.get("sections", []),
            "profiles": profiles_payload,
            "survey": [r.model_dump(mode="json") for r in state.survey_results.values()],
            "language": language,
        }
        markdown = payload.get("markdown") or "# Competitor Analysis Report\n"
        return self._build_report(state, structured_content, markdown, claims, sources, language)

    def _run_fallback(self, state: WorkflowState, *, language: str) -> Report:
        claims: list[ReportClaim] = []
        sources = [s for result in state.raw_collections.values() for s in result.sources]

        for index, (name, profile) in enumerate(state.structured_profiles.items(), start=1):
            claims.append(
                ReportClaim(
                    claim_path=f"profiles[{index}].summary",
                    claim_text=f"{name} has collaboration and reporting features.",
                    layer="core",
                    field_type="structured",
                    source_ids=profile.source_ids,
                    generating_agent="WriterAgent",
                    source_support="supported",
                    validity="valid",
                )
            )

        evidence_index = {
            e.id: e
            for survey in state.survey_results.values()
            for e in survey.evidence
        }
        for index, (_, survey) in enumerate(state.survey_results.items(), start=1):
            for insight_index, insight in enumerate(survey.insights, start=1):
                source_support = "supported" if insight.confidence != "low" else "weak"
                all_simulated = insight.evidence_ids and all(
                    evidence_index.get(eid) is not None
                    and evidence_index[eid].source_type == "ai_simulated"
                    for eid in insight.evidence_ids
                )
                claim_text = (
                    f"⚠️ [AI模拟] {insight.point}" if all_simulated else insight.point
                )
                claims.append(
                    ReportClaim(
                        claim_path=f"survey[{index}].insights[{insight_index}]",
                        claim_text=claim_text,
                        layer="survey",
                        field_type="free_text",
                        source_ids=insight.evidence_ids,
                        generating_agent="SurveyTool",
                        source_support=source_support,
                        validity="valid",
                    )
                )

        profiles_payload = [p.model_dump(mode="json") for p in state.structured_profiles.values()]
        structured_content = {
            "summary": "S0 mock report generated by the backend skeleton.",
            "profiles": profiles_payload,
            "survey": [r.model_dump(mode="json") for r in state.survey_results.values()],
            "language": language,
        }
        markdown = "# Competitor Analysis Report\n\nS0 mock report with traceable claims.\n"
        return self._build_report(state, structured_content, markdown, claims, sources, language)

    def _claims_from_payload(self, payload: dict, state: WorkflowState) -> list[ReportClaim]:
        claims: list[ReportClaim] = []
        fallback_source_ids = {
            name: profile.source_ids for name, profile in state.structured_profiles.items()
        }
        for index, item in enumerate(payload.get("claims", []), start=1):
            competitor_name = str(item.get("competitor_name") or item.get("competitor", ""))
            source_ids = item.get("source_ids") or fallback_source_ids.get(competitor_name, [])
            claims.append(
                ReportClaim(
                    claim_path=str(item.get("claim_path", f"claims[{index}]")),
                    claim_text=str(item.get("claim_text", "")),
                    layer=item.get("layer", "core"),
                    field_type=item.get("field_type", "free_text"),
                    source_ids=source_ids,
                    generating_agent="WriterAgent",
                    source_support="supported" if source_ids else "unchecked",
                    validity="valid" if source_ids else "unknown",
                )
            )
        if claims:
            return claims
        for index, (name, profile) in enumerate(state.structured_profiles.items(), start=1):
            claims.append(
                ReportClaim(
                    claim_path=f"profiles[{index}].summary",
                    claim_text=f"{name} has structured competitive signals.",
                    layer="core",
                    field_type="structured",
                    source_ids=profile.source_ids,
                    generating_agent="WriterAgent",
                    source_support="supported",
                    validity="valid",
                )
            )
        return claims

    def _build_report(
        self,
        state: WorkflowState,
        structured_content: dict,
        markdown: str,
        claims: list[ReportClaim],
        sources: list,
        language: str,
    ) -> Report:
        metrics = calculate_report_metrics(
            claims=claims,
            sources=sources,
            rerun_count=sum(state.retry_counts.values()),
            module_count=max(len(state.scope_contract.dimensions), 1),
            ai_self_assessment={"confidence": "needs_review", "needs_human_review": True},
        )
        return Report(
            task_id=UUID(str(state.task_id)),
            language="zh" if language not in {"zh", "en"} else language,
            structured_content=structured_content,
            markdown_content=markdown,
            sources=sources,
            claims=claims,
            metrics=metrics,
            qa_status="issues" if state.qa_result and not state.qa_result.passed else "passed",
            qa_issues=(
                [issue.model_dump(mode="json") for issue in state.qa_result.issues]
                if state.qa_result
                else []
            ),
        )


def _build_simulated_warnings(state: WorkflowState) -> list[dict]:
    """Return a list of survey competitors whose evidence is predominantly AI-simulated."""
    warnings = []
    for competitor, survey in state.survey_results.items():
        if not survey.evidence:
            continue
        simulated = sum(1 for e in survey.evidence if e.source_type == "ai_simulated")
        ratio = simulated / len(survey.evidence)
        if ratio > 0:
            warnings.append({
                "competitor": competitor,
                "ai_simulated_ratio": round(ratio, 2),
                "note": "⚠️ mark required on insights from simulated evidence",
            })
    return warnings
