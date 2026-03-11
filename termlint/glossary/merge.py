"""Glossary merge logic."""

from dataclasses import replace
from typing import Dict, List

from termlint.core.models import Entity
from termlint.glossary.models import (
    ConflictPolicy,
    MatchPolicy,
    MergeConflict,
    MergePolicy,
    MergeResult,
    MergeSummary,
)
from termlint.glossary.utils import canonical_term


def merge_entities(
    base: List[Entity],
    updates: List[Entity],
    policy: MergePolicy,
) -> MergeResult:
    """Merge update entities into base glossary with conflict policies."""
    merged: List[Entity] = list(base)
    conflicts: List[MergeConflict] = []

    added = 0
    updated = 0
    skipped = 0

    id_to_index: Dict[str, int] = {entity.id: idx for idx, entity in enumerate(merged)}
    term_to_ids: Dict[str, set[str]] = {}
    for entity in merged:
        _index_entity_terms(term_to_ids, entity)

    for candidate in updates:
        by_id_index = id_to_index.get(candidate.id)
        term_matches = _find_term_matches(term_to_ids, candidate)

        # Conflict: same ID points to different canonical label
        if by_id_index is not None:
            base_entity = merged[by_id_index]
            if canonical_term(base_entity.label) != canonical_term(candidate.label):
                conflict = MergeConflict(
                    conflict_type="id_label_mismatch",
                    message="Update entity ID already exists with a different label",
                    base_id=base_entity.id,
                    update_id=candidate.id,
                    raw_data={"base_label": base_entity.label, "update_label": candidate.label},
                )
                _apply_conflict_policy(
                    merged=merged,
                    id_to_index=id_to_index,
                    term_to_ids=term_to_ids,
                    conflicts=conflicts,
                    conflict=conflict,
                    policy=policy,
                    candidate=candidate,
                    target_index=by_id_index,
                )
                if policy.on_conflict == ConflictPolicy.KEEP_UPDATE:
                    updated += 1
                elif policy.on_conflict == ConflictPolicy.REPORT:
                    skipped += 1
                else:
                    skipped += 1
                continue

        # Conflict: candidate maps to multiple existing entities by term
        if len(term_matches) > 1:
            conflict = MergeConflict(
                conflict_type="ambiguous_term_match",
                message="Update term matches multiple base entities",
                update_id=candidate.id,
                raw_data={"matched_ids": sorted(term_matches), "candidate_label": candidate.label},
            )
            _apply_conflict_policy(
                merged=merged,
                id_to_index=id_to_index,
                term_to_ids=term_to_ids,
                conflicts=conflicts,
                conflict=conflict,
                policy=policy,
                candidate=candidate,
                target_index=None,
            )
            if policy.on_conflict == ConflictPolicy.REPORT:
                skipped += 1
            elif policy.on_conflict == ConflictPolicy.KEEP_UPDATE:
                _append_entity(merged, id_to_index, term_to_ids, candidate)
                added += 1
            else:
                skipped += 1
            continue

        # Match by term to a single entity
        if len(term_matches) == 1:
            target_id = next(iter(term_matches))
            target_index = id_to_index[target_id]
            action = _apply_match_policy(merged, target_index, candidate, policy.on_match)
            if action == "updated":
                # Rebuild term index for updated entity.
                term_to_ids.clear()
                for entity in merged:
                    _index_entity_terms(term_to_ids, entity)
                updated += 1
            else:
                skipped += 1
            continue

        # Match by ID with same label already handled above. No match -> append.
        _append_entity(merged, id_to_index, term_to_ids, candidate)
        added += 1

    summary = MergeSummary(
        added=added,
        updated=updated,
        skipped=skipped,
        conflicts=len(conflicts),
    )
    return MergeResult(
        merged=merged,
        conflicts=conflicts,
        summary=summary
    )


def _apply_match_policy(
    merged: List[Entity],
    target_index: int,
    candidate: Entity,
    match_policy: MatchPolicy,
) -> str:
    base_entity = merged[target_index]
    if match_policy == MatchPolicy.SKIP:
        return "skipped"
    if match_policy == MatchPolicy.REPLACE:
        merged[target_index] = candidate
        return "updated"

    # merge-synonyms
    synonyms = _merge_synonyms(base_entity, candidate)
    definition = base_entity.definition or candidate.definition
    source = base_entity.source or candidate.source
    merged[target_index] = replace(
        base_entity,
        synonyms=synonyms,
        definition=definition,
        source=source,
    )
    return "updated"


def _apply_conflict_policy(
    merged: List[Entity],
    id_to_index: Dict[str, int],
    term_to_ids: Dict[str, set[str]],
    conflicts: List[MergeConflict],
    conflict: MergeConflict,
    policy: MergePolicy,
    candidate: Entity,
    target_index: int | None,
) -> None:
    if policy.on_conflict == ConflictPolicy.REPORT:
        conflicts.append(conflict)
        return
    if policy.on_conflict == ConflictPolicy.KEEP_BASE:
        return
    if target_index is not None:
        merged[target_index] = candidate
    else:
        _append_entity(merged, id_to_index, term_to_ids, candidate)


def _append_entity(
    merged: List[Entity],
    id_to_index: Dict[str, int],
    term_to_ids: Dict[str, set[str]],
    candidate: Entity,
) -> None:
    if candidate.id in id_to_index:
        suffix = 1
        new_id = candidate.id
        while new_id in id_to_index:
            suffix += 1
            new_id = f"{candidate.id}_{suffix}"
        candidate = replace(candidate, id=new_id)

    id_to_index[candidate.id] = len(merged)
    merged.append(candidate)
    _index_entity_terms(term_to_ids, candidate)


def _merge_synonyms(base_entity: Entity, candidate: Entity) -> List[str]:
    existing = {canonical_term(base_entity.label)}
    merged: List[str] = []
    seen: set[str] = set()
    for raw in [*base_entity.synonyms, *candidate.synonyms, candidate.label]:
        key = canonical_term(raw)
        if not key or key in existing or key in seen:
            continue
        seen.add(key)
        merged.append(key)
    return merged


def _find_term_matches(term_to_ids: Dict[str, set[str]], entity: Entity) -> set[str]:
    matched: set[str] = set()
    for raw in [entity.label, *entity.synonyms]:
        key = canonical_term(raw)
        if key and key in term_to_ids:
            matched.update(term_to_ids[key])
    return matched


def _index_entity_terms(term_to_ids: Dict[str, set[str]], entity: Entity) -> None:
    for raw in [entity.label, *entity.synonyms]:
        key = canonical_term(raw)
        if not key:
            continue
        term_to_ids.setdefault(key, set()).add(entity.id)
