from schemas.survey import DistributionHandle, Questionnaire, SurveyResponse, TargetPersona

_FALLBACK_PERSONA = TargetPersona(
    label="模拟受访者",
    traits="无真实用户声音时的最小兜底画像。",
    est_size="niche",
    inferred_from=[],
)

# Simulated answer templates vary by index to avoid identical responses
_ANSWER_TEMPLATES = [
    "该产品的{feature}功能符合预期，价格合理，整体满意度较高。",
    "在使用过程中，{feature}方面有待改善，但核心体验流畅。",
    "对比竞品，该产品的{feature}有明显优势，会推荐给同事。",
    "购买决策主要基于{feature}能力与团队需求的匹配程度。",
    "希望在{feature}方面继续迭代，目前体验一般。",
]


class SimulatedDistributor:
    def __init__(self) -> None:
        # Keyed by DistributionHandle.id to avoid state clobbering under concurrent use.
        self._pending: dict[str, Questionnaire] = {}

    def distribute(
        self,
        questionnaire: Questionnaire,
        target_personas: list[TargetPersona],
        sample_size: int,
    ) -> DistributionHandle:
        handle = DistributionHandle(
            distributor_impl=self.__class__.__name__,
            questionnaire_id=questionnaire.id,
            target_personas=target_personas,
            sample_size=sample_size,
            status="completed",
        )
        self._pending[handle.id] = questionnaire
        return handle

    def collect_responses(self, handle: DistributionHandle) -> list[SurveyResponse]:
        questionnaire = self._pending.pop(handle.id, None)
        if questionnaire is None:
            return []
        personas = handle.target_personas or [_FALLBACK_PERSONA]
        # Generate sample_size responses, cycling through available personas
        count = max(handle.sample_size, len(personas), 1)
        responses: list[SurveyResponse] = []
        for i in range(count):
            persona = personas[i % len(personas)]
            template = _ANSWER_TEMPLATES[i % len(_ANSWER_TEMPLATES)]
            answers = {
                question.id: template.format(feature=question.intent[:20])
                for question in questionnaire.questions
            }
            responses.append(
                SurveyResponse(
                    distribution_id=handle.id,
                    persona=persona,
                    answers=answers,
                )
            )
        return responses
