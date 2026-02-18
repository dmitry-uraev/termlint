"""
ExactVerification stage: TextEntityStream -> MatchResultStream
"""

from typing import Dict, List

from termlint.core.stages import ProcessingStage
from termlint.core.types import Result, TextEntityStream, MatchResultStream
from termlint.core.models import TextEntity, MatchResult, MatchStatus, Entity
from termlint.verifier.sources import KnowledgeSource
from termlint.utils.logger import get_child_logger


logger = get_child_logger(file_path='VerificationStage (Exact)')


class ExactVerificationStage(ProcessingStage[TextEntityStream, MatchResultStream]):
    """
    Matches TextEntity candidates against KnowledgeSource

    Algorithm: exact matching (term or lemma)
    """

    def __init__(self, source: KnowledgeSource, min_confidence: float = 0.5) -> None:
        self.source = source
        self.min_confidence = min_confidence

    async def _process_entities(self, entities: List[TextEntity]) -> Result[List[MatchResult]]:
        """Match all entities"""
        if not entities:
            return Result.ok([])

        unique_terms = list({e.text for e in entities} | {e.lemma for e in entities})
        entities_result = await self.source.get_entities(unique_terms)

        if not entities_result.is_ok:
            logger.warning(f"Batch lookup failed: {entities_result.errors}")
            matches = [self._unknown_match(entity) for entity in entities]
            return Result.ok(matches)

        term_to_entity: Dict[str, Entity] = {
            entity.label.lower(): entity
            for entity in entities_result.value
        }

        matches = []
        for text_entity in entities:
            match_result = self._create_match(text_entity, term_to_entity)
            matches.append(match_result)

        logger.debug(f"Batch matched {len([m for m in matches if m.status == MatchStatus.MATCHED])}/{len(entities)}")
        return Result.ok(matches)

    def _create_match(self, text_entity: TextEntity, term_index: Dict[str, Entity]) -> MatchResult:
        text_lower = text_entity.text.lower()
        lemma_lower = text_entity.lemma.lower()

        # Exact
        if text_lower in term_index:
            entity = term_index[text_lower]
            return MatchResult(
                text_entity=text_entity,
                entity=entity,
                confidence=1.0,
                status=MatchStatus.MATCHED,
                matched_synonym=text_entity.text
            )

        # Lemma
        if lemma_lower in term_index:
            entity = term_index[lemma_lower]
            return MatchResult(
                text_entity=text_entity,
                entity=entity,
                confidence=0.9,
                status=MatchStatus.MATCHED,
                matched_synonym=text_entity.lemma
            )

        # unknown
        return self._unknown_match(text_entity)

    def _unknown_match(self, text_entity: TextEntity) -> MatchResult:
        """Unknown match fallback"""
        logger.debug(f"Unknown: '{text_entity.text}' (lemma: '{text_entity.lemma}')")
        return MatchResult(
            text_entity=text_entity,
            confidence=0.0,
            status=MatchStatus.UNKNOWN
        )

    async def process(self, stream: TextEntityStream) -> Result[MatchResultStream]:
        """TextEntityStream -> MatchResultStream"""
        collect_result = await stream.to_list()
        matches_result = await collect_result.bind(self._process_entities)
        return matches_result.map(lambda matches: MatchResultStream.from_list(matches))
