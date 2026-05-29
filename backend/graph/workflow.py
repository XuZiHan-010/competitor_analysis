from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.analyst import AnalystAgent
from agents.collector import CollectorAgent
from agents.qa import QAAgent
from agents.writer import WriterAgent
from graph.state import WorkflowState

MAX_COLLECTOR_RETRIES = 3


class GraphState(TypedDict, total=False):
    task_id: str
    run_id: str
    scope_contract: dict[str, Any]
    raw_collections: dict[str, Any]
    structured_profiles: dict[str, Any]
    extension_findings: list[dict[str, Any]]
    survey_results: dict[str, Any]
    uploaded_survey_evidence: list[dict[str, Any]]
    cross_analysis: dict[str, Any] | None
    report: dict[str, Any] | None
    qa_result: dict[str, Any] | None
    feedback_signals: dict[str, Any]
    retry_counts: dict[str, int]


def _trace_ctx(config: RunnableConfig) -> Any:
    return (config.get("configurable") or {}).get("trace_context")


async def _collector_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    ws = WorkflowState.model_validate(state)
    raw_collections, survey_results = await CollectorAgent().run(
        ws, trace_context=_trace_ctx(config)
    )
    return {
        "raw_collections": {k: v.model_dump(mode="json") for k, v in raw_collections.items()},
        "survey_results": {k: v.model_dump(mode="json") for k, v in survey_results.items()},
    }


async def _analyst_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    ws = WorkflowState.model_validate(state)
    structured_profiles, extension_findings, cross_analysis = await AnalystAgent().run(
        ws, trace_context=_trace_ctx(config)
    )
    return {
        "structured_profiles": {
            k: v.model_dump(mode="json") for k, v in structured_profiles.items()
        },
        "extension_findings": [f.model_dump(mode="json") for f in extension_findings],
        "cross_analysis": cross_analysis.model_dump(mode="json") if cross_analysis else None,
    }


async def _qa_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    ws = WorkflowState.model_validate(state)
    qa_result = await QAAgent().run(ws, trace_context=_trace_ctx(config))
    retry_counts = dict(state.get("retry_counts") or {})
    feedback_signals = dict(state.get("feedback_signals") or {})
    if qa_result and not qa_result.passed:
        retry_counts["collector"] = retry_counts.get("collector", 0) + 1
        blocker_issues = [issue for issue in qa_result.issues if issue.severity == "blocker"]
        feedback_signals["correction_detected"] = {
            "target_agent": "CollectorAgent",
            "retry_count": retry_counts["collector"],
            "issues": [issue.model_dump(mode="json") for issue in blocker_issues],
        }
    return {
        "qa_result": qa_result.model_dump(mode="json") if qa_result else None,
        "retry_counts": retry_counts,
        "feedback_signals": feedback_signals,
    }


async def _writer_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    ws = WorkflowState.model_validate(state)
    report = await WriterAgent().run(ws, trace_context=_trace_ctx(config))
    return {"report": report.model_dump(mode="json") if report else None}


def _route_after_qa(state: GraphState) -> str:
    qa = state.get("qa_result") or {}
    retries = (state.get("retry_counts") or {}).get("collector", 0)
    if not qa.get("passed", True) and retries < MAX_COLLECTOR_RETRIES:
        return "collect"
    return "write"


def create_workflow_graph(checkpointer: Any = None) -> Any:
    graph: StateGraph = StateGraph(GraphState)
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
    initial: dict[str, Any] = state.model_dump(mode="json")
    config: RunnableConfig = {
        "configurable": {
            "thread_id": str(state.run_id),
            "trace_context": trace_context,
        }
    }
    result: dict[str, Any] = await graph.ainvoke(initial, config=config)
    return WorkflowState.model_validate(result)
