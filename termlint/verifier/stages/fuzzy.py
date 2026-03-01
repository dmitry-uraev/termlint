"""
FuzzyVerification stage: TextEntityStream -> MatchResultStream
"""

from rapidfuzz import process, fuzz

from termlint.core.stages import ProcessingStage
from termlint.core.types import Result, TextEntityStream, MatchResultStream
from termlint.core.models import TextEntity, MatchResult, MatchStatus
from termlint.verifier.sources import KnowledgeSource
from termlint.utils.logger import get_child_logger


logger = get_child_logger(file_path='VerificationStage (Fuzzy)')


class FuzzyVerificationStage(ProcessingStage[TextEntityStream, MatchResultStream]):
    """
    Matches TextEntity candidates against KnowledgeSource

    Algorithm: fuzzy matching (term or lemma)
    """

    def __init__(self, source: KnowledgeSource, threshold: int, scorer: str, limit: int,) -> None:
        self.source = source
        self.threshold = threshold  # match %
        self.scorer = getattr(fuzz, scorer)  # ratio, partial_ratio, token_set_ratio
        self.limit = limit  # top N candidates
        self.use_lemma = True  # takes lemma if present

        # TODO: provide convenient getter from source?
        self._glossary_terms = list(source.index.keys()) if source.index else []
        logger.info(f"Fuzzy init: threshold={threshold}, terms={len(source.index)}")

    async def process(self, stream: TextEntityStream) -> Result[MatchResultStream]:
        """TextEntityStream → MatchResultStream"""
        matches = []
        async for entity in stream:
            logger.debug(f"Processing: '{entity.text}'")
            candidate_text = self._prepare_text(entity)
            match_result = await self._find_best_match(entity, candidate_text)
            matches.append(match_result)

        matched = sum(1 for m in matches if m.status == MatchStatus.NEAR_MATCH)
        logger.info(f"Processed {len(matches)} entities -> {matched} fuzzy matches")
        return Result.ok(MatchResultStream.from_list(matches))

    def _prepare_text(self, entity) -> str:
        """Choose text for match depending on setup parameters"""
        if self.use_lemma and entity.lemma:
            text = entity.lemma
        else:
            text = entity.text

        return text

    async def _find_best_match(self, entity: TextEntity, query: str) -> MatchResult:
        """Find best fuzzy match in glossary"""
        if not query:
            return MatchResult(
                text_entity=entity,
                status=MatchStatus.UNKNOWN
            )

        results  =process.extract(
            query,
            self._glossary_terms,
            scorer=self.scorer,
            limit=self.limit,
            score_cutoff=self.threshold
        )
        logger.debug(f"Matches for '{query}': {results}")

        if results:
            best_term, best_score, _ = results[0]
            entities_list = self.source.index.get(best_term)
            matched_entity = entities_list[0] if entities_list else None

            return MatchResult(
                text_entity=entity,
                entity=matched_entity,
                confidence=best_score / 100.,
                status=MatchStatus.NEAR_MATCH,
                matched_synonym=best_term
            )

        return MatchResult(
            text_entity=entity,
            status=MatchStatus.UNKNOWN
        )
