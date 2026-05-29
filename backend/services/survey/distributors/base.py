from typing import Protocol

from schemas.survey import DistributionHandle, Questionnaire, SurveyResponse, TargetPersona


class SurveyDistributor(Protocol):
    def distribute(
        self,
        questionnaire: Questionnaire,
        target_personas: list[TargetPersona],
        sample_size: int,
    ) -> DistributionHandle: ...

    def collect_responses(self, handle: DistributionHandle) -> list[SurveyResponse]: ...
