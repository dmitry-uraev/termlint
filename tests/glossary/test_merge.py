from termlint.core.models import Entity
from termlint.glossary.merge import merge_entities
from termlint.glossary.models import ConflictPolicy, MatchPolicy, MergePolicy


def test_merge_entities_merges_synonyms_on_term_match():
    base = [
        Entity(id="ml:001", label="machine learning", synonyms=["ml"]),
    ]
    updates = [
        Entity(id="auto:abc", label="machine learning", synonyms=["machine intelligence"]),
    ]

    merged, conflicts, summary = merge_entities(
        base,
        updates,
        MergePolicy(on_match=MatchPolicy.MERGE_SYNONYMS, on_conflict=ConflictPolicy.REPORT),
    )

    assert len(merged) == 1
    assert len(conflicts) == 0
    assert summary.updated == 1
    assert "machine intelligence" in merged[0].synonyms


def test_merge_entities_reports_id_label_conflict():
    base = [
        Entity(id="ml:001", label="machine learning", synonyms=[]),
    ]
    updates = [
        Entity(id="ml:001", label="deep learning", synonyms=[]),
    ]

    merged, conflicts, summary = merge_entities(
        base,
        updates,
        MergePolicy(on_match=MatchPolicy.MERGE_SYNONYMS, on_conflict=ConflictPolicy.REPORT),
    )

    assert len(merged) == 1
    assert len(conflicts) == 1
    assert summary.conflicts == 1
    assert summary.skipped == 1
