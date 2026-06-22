from graph.state import WorkflowState


def has_retry_correction(state: WorkflowState) -> bool:
    return isinstance(state.feedback_signals.get("correction_detected"), dict)


def retry_target_competitors(state: WorkflowState) -> set[str] | None:
    """Return precise retry targets, or None when correctness requires a full retry."""
    correction = state.feedback_signals.get("correction_detected")
    if not isinstance(correction, dict):
        return None
    issues = correction.get("issues")
    if not isinstance(issues, list) or not issues:
        return None

    known = {competitor.name for competitor in state.scope_contract.competitors}
    targets: set[str] = set()
    for issue in issues:
        if not isinstance(issue, dict):
            return None
        target = issue.get("target_competitor")
        if not isinstance(target, str) or not target.strip():
            return None
        target = target.strip()
        if target not in known:
            return None
        targets.add(target)
    return targets or None
