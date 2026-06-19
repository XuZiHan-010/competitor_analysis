from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.analyst import AnalystAgent
from agents.collector import CollectorAgent
from agents.qa import QAAgent
from agents.writer import WriterAgent
from graph.state import WorkflowState

MAX_COLLECTOR_RETRIES = 3


def _trace_ctx(config: RunnableConfig) -> Any:
    return (config.get("configurable") or {}).get("trace_context")


# Nodes receive a validated WorkflowState (LangGraph builds it from the channels)
# but must return JSON-serializable updates: the checkpointer serializes channel
# writes via msgpack, which cannot encode raw Pydantic model instances.
async def _collector_node(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    trace_context = _trace_ctx(config)
    raw_collections, survey_results = await CollectorAgent().run(
        state, trace_context=trace_context
    )
    # A competitor with zero real sources means every downstream section for it
    # will be empty; surface that on the live event stream now instead of letting
    # the viewer discover a blank report minutes later.
    publish = getattr(trace_context, "publish_event", None)
    if publish is not None:
        for name, collection in raw_collections.items():
            if not collection.has_real_sources():
                await publish(
                    "collector.degraded",
                    {"competitor": name, "errors": collection.errors},
                )
    return {
        "raw_collections": {k: v.model_dump(mode="json") for k, v in raw_collections.items()},
        "survey_results": {k: v.model_dump(mode="json") for k, v in survey_results.items()},
    }


async def _analyst_node(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    structured_profiles, extension_findings, cross_analysis = await AnalystAgent().run(
        state, trace_context=_trace_ctx(config)
    )
    return {
        "structured_profiles": {
            k: v.model_dump(mode="json") for k, v in structured_profiles.items()
        },
        "extension_findings": [f.model_dump(mode="json") for f in extension_findings],
        "cross_analysis": cross_analysis.model_dump(mode="json") if cross_analysis else None,
    }


async def _qa_node(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    qa_result = await QAAgent().run(state, trace_context=_trace_ctx(config))
    retry_counts = dict(state.retry_counts)
    feedback_signals = dict(state.feedback_signals)
    field_verification_status = dict(state.field_verification_status)
    if qa_result and not qa_result.passed:
        blocker_issues = [issue for issue in qa_result.issues if issue.severity == "blocker"]
        retryable_blockers = [issue for issue in blocker_issues if issue.retryable]
        # Only count and signal a retry when one can actually help; a blocker
        # caused by exhausted search quota fails identically on every loop.
        if retryable_blockers:
            retry_counts["collector"] = retry_counts.get("collector", 0) + 1
            feedback_signals["correction_detected"] = {
                "target_agent": "CollectorAgent",
                "retry_count": retry_counts["collector"],
                "issues": [issue.model_dump(mode="json") for issue in retryable_blockers],
            }
        if not retryable_blockers or retry_counts["collector"] >= MAX_COLLECTOR_RETRIES:
            for issue in blocker_issues:
                if not issue.target_competitor:
                    continue
                field_path = issue.failed_field
                key = f"{issue.target_competitor}.{field_path}"
                field_verification_status[key] = {
                    "competitor": issue.target_competitor,
                    "field_path": field_path,
                    "status": "unverified",
                    "reason": issue.message,
                    "source_ids": [],
                }
    return {
        "qa_result": qa_result.model_dump(mode="json") if qa_result else None,
        "retry_counts": retry_counts,
        "feedback_signals": feedback_signals,
        "field_verification_status": field_verification_status,
    }


async def _writer_node(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    report = await WriterAgent().run(
        state, trace_context=_trace_ctx(config), language=state.report_language
    )
    return {"report": report.model_dump(mode="json") if report else None}


def _route_after_qa(state: WorkflowState) -> str:
    if state.qa_result is None or state.qa_result.passed:
        return "write"
    retryable_blockers = [
        issue
        for issue in state.qa_result.issues
        if issue.severity == "blocker" and issue.retryable
    ]
    if retryable_blockers and state.retry_counts.get("collector", 0) < MAX_COLLECTOR_RETRIES:
        return "collect"
    return "write"


def create_workflow_graph(checkpointer: Any = None) -> Any:
    graph: StateGraph = StateGraph(WorkflowState)
    graph.add_node("collect", _collector_node)
    graph.add_node("analyze", _analyst_node)
    graph.add_node("qa_check", _qa_node)
    graph.add_node("write", _writer_node)
    graph.set_entry_point("collect")
    graph.add_edge("collect", "analyze")
    graph.add_edge("analyze", "qa_check")
    graph.add_conditional_edges(
        "qa_check",
        _route_after_qa,
        {"collect": "collect", "write": "write"},
    )
    graph.add_edge("write", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


async def run_workflow(
    state: WorkflowState,
    *,
    trace_context: object,
    checkpointer: Any = None,
) -> WorkflowState:
    graph = create_workflow_graph(checkpointer=checkpointer)
    config: RunnableConfig = {
        "configurable": {
            "thread_id": str(state.run_id),
            "trace_context": trace_context,
        }
    }
    result: Any = await graph.ainvoke(state, config=config)
    if isinstance(result, WorkflowState):
        return result
    return WorkflowState.model_validate(result)
