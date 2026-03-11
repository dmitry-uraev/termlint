from typing import Dict, List

from termlint.core.models import Entity, TextEntity
from termlint.core.types import EntityStream, MatchResultStream, Result, TextEntityStream

from termlint.glossary.utils import canonical_term, stable_id


class DefaultTextEntityBuilder:
    def __init__(
        self,
        namespace: str = "auto",
        min_score: float = 0.0,
        min_frequency: int = 1,
    ) -> None:
        self.namespace = namespace
        self.min_score = min_score
        self.min_frequency = min_frequency

    async def build(self, stream: TextEntityStream) -> Result[EntityStream]:
        """
        Converts TextEntityStream -> EntityStream

        "text_entity": {
            "text": "большие данные",
            "original_text": "большие данные",
            "lemma": "большие данные",
            "span": [
                47,
                61
            ],
            "score": 1.0,
            "pos_tags": [],
            "sentence": "",
            "frequency": 1,
            "extractor_type": "cvalue_normalized",
            "properties": {
                "length": 2
            }
        }

        ->

        "entity": {
            "id": "ml:cc7b1d20c4",
            "label": "большие данные",
            "synonyms": [],
            "relations": {},
            "definition": "",
            "source": "termlint:ontology_update"
        }
        """
        grouped: Dict[str, List[TextEntity]] = {}
        async for e in stream:
            if e.score < self.min_score or e.score < self.min_frequency:
                continue

            key_source = e.lemma or e.text or e.original_text
            key = canonical_term(key_source)
            if not key:
                continue

            grouped.setdefault(key, []).append(e)

        used_ids: set[str] = set()
        result: List[Entity] = []

        for canonical_key in sorted(grouped.keys()):
            group = grouped[canonical_key]
            entity_id = stable_id(namespace=self.namespace, canonical_key=canonical_key, used_ids=used_ids)
            used_ids.add(entity_id)

            synonyms_seen: set[str] = set()
            synonyms: List[str] = []
            for candidate in group:
                for raw in (candidate.original_text, candidate.text):
                    normalized = canonical_term(raw)
                    if not normalized or normalized == canonical_key:
                        continue
                    if normalized in synonyms_seen:
                        continue
                    synonyms_seen.add(normalized)
                    synonyms.append(normalized)

            result.append(
                Entity(
                    id=entity_id,
                    label=canonical_key,
                    synonyms=synonyms,
                    relations={},
                    definition=None,
                    source="termlint:entity_from_text"
                )
            )
        return Result.ok(EntityStream.from_list(result))


class DefaultMatchResultEntityBuilder:
    """
    Implementation detail: DefaultMatchResultEntityBuilder will likely
        transform selected MatchResult items into TextEntity candidates
        first, then reuse the same normalization logic as the text builder.
    """
    def __init__(
        self,
        namespace: str = "auto",
        min_score: float = 0.0,
        min_frequency: int = 1,
    ) -> None:
        self.namespace = namespace
        self.min_score = min_score
        self.min_frequency = min_frequency

    async def build(self, stream: MatchResultStream) -> Result[EntityStream]:
        ...
