"""DEPRECATED: Convert ontology update report candidates to glossary entities."""

from typing import Dict, List

from termlint.core.models import Entity, TextEntity
from termlint.glossary.utils import canonical_term, stable_id


def convert_candidates_to_entities(
    candidates: List[TextEntity],
    namespace: str = "auto",
    min_score: float = 0.0,
    min_frequency: int = 1,
) -> List[Entity]:
    """Convert extracted candidates to deduplicated glossary entities."""
    grouped: Dict[str, List[TextEntity]] = {}
    for candidate in candidates:
        if candidate.score < min_score:
            continue
        if candidate.frequency < min_frequency:
            continue

        key_source = candidate.lemma or candidate.text or candidate.original_text
        key = canonical_term(key_source)
        if not key:
            continue
        grouped.setdefault(key, []).append(candidate)

    used_ids: set[str] = set()
    result: List[Entity] = []
    for canonical_key in sorted(grouped.keys()):
        group = grouped[canonical_key]
        entity_id = stable_id(namespace=namespace, canonical_key=canonical_key, used_ids=used_ids)
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
                source="termlint:ontology_update",
            )
        )
    return result
