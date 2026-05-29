from graph.state import RawCollectionResult
from schemas.survey import TargetPersona


class PersonaInferrer:
    def infer(self, result: RawCollectionResult) -> list[TargetPersona]:
        source_ids = [source.id for source in result.sources[:3]]
        return [
            TargetPersona(
                label="核心决策用户",
                traits="关注价格、功能完整性和团队落地效率。",
                est_size="significant",
                inferred_from=source_ids,
            )
        ]
