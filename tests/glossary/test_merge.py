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

    merge_result = merge_entities(
        base,
        updates,
        MergePolicy(on_match=MatchPolicy.MERGE_SYNONYMS, on_conflict=ConflictPolicy.REPORT),
    )

    assert len(merge_result.merged) == 1
    assert len(merge_result.conflicts) == 0
    assert merge_result.summary.updated == 1
    assert "machine intelligence" in merge_result.merged[0].synonyms


def test_merge_entities_reports_id_label_conflict():
    base = [
        Entity(id="ml:001", label="machine learning", synonyms=[]),
    ]
    updates = [
        Entity(id="ml:001", label="deep learning", synonyms=[]),
    ]

    merge_result = merge_entities(
        base,
        updates,
        MergePolicy(on_match=MatchPolicy.MERGE_SYNONYMS, on_conflict=ConflictPolicy.REPORT),
    )

    assert len(merge_result.merged) == 1
    assert len(merge_result.conflicts) == 1
    assert merge_result.summary.conflicts == 1
    assert merge_result.summary.skipped == 1
