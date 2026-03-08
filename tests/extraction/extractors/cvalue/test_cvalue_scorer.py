import math

from termlint.extraction.extractors.cvalue_support.scorer import CValueScorer


def scores_by_text(results):
    """Convert scorer output into a mapping keyed by candidate text."""
    return {text: (score, freq, indices) for text, score, freq, indices in results}


def test_returns_empty_for_empty_candidates():
    scorer = CValueScorer()
    assert scorer.compute([]) == []


def test_single_multiword_candidate_without_nesting():
    scorer = CValueScorer()

    results = scorer.compute([
        ("machine learning", [0, 1]),
    ])
    by_text = scores_by_text(results)

    assert "machine learning" in by_text
    score, freq, indices = by_text["machine learning"]

    assert freq == 1
    assert indices == [0, 1]
    assert score == math.log2(2) * 1


def test_repeated_candidate_frequency_increases_score():
    scorer = CValueScorer()

    results = scorer.compute([
        ("machine learning", [0, 1]),
        ("machine learning", [2, 3]),
    ])
    by_text = scores_by_text(results)

    score, freq, indices = by_text["machine learning"]

    assert freq == 2
    assert indices == [0, 1]
    assert score == math.log2(2) * 2


def test_single_token_candidate_has_zero_score():
    scorer = CValueScorer()

    results = scorer.compute([
        ("learning", [0]),
    ])
    by_text = scores_by_text(results)

    score, freq, indices = by_text["learning"]

    assert freq == 1
    assert indices == [0]
    assert score == 0.0


def test_nested_candidate_is_penalized_to_zero_when_parent_has_same_frequency():
    scorer = CValueScorer()

    results = scorer.compute([
        ("machine learning", [0, 1]),
        ("machine learning methods", [0, 1, 2]),
    ])
    by_text = scores_by_text(results)

    short_score, short_freq, _ = by_text["machine learning"]
    long_score, long_freq, _ = by_text["machine learning methods"]

    assert short_freq == 1
    assert long_freq == 1
    assert short_score == 0.0
    assert long_score == math.log2(3) * 1


def test_nested_term_uses_average_parent_frequency():
    scorer = CValueScorer()

    results = scorer.compute([
        ("machine learning", [0, 1]),
        ("machine learning", [3, 4]),
        ("machine learning methods", [0, 1, 2]),
        ("machine learning systems", [3, 4, 5]),
    ])
    by_text = scores_by_text(results)

    score, freq, _ = by_text["machine learning"]

    # freq("machine learning") = 2
    # parent freqs = [1, 1]
    # avg parent freq = 1
    # score = log2(2) * (2 - 1) = 1
    assert freq == 2
    assert score == math.log2(2) * (2 - 1)


def test_longer_non_nested_candidate_keeps_higher_score():
    scorer = CValueScorer()

    results = scorer.compute([
        ("deep learning", [0, 1]),
        ("artificial intelligence systems", [2, 3, 4]),
    ])
    by_text = scores_by_text(results)

    short_score, _, _ = by_text["deep learning"]
    long_score, _, _ = by_text["artificial intelligence systems"]

    assert short_score == math.log2(2)
    assert long_score == math.log2(3)
    assert long_score > short_score


def test_min_freq_filters_rare_candidates():
    scorer = CValueScorer(min_freq=2)

    results = scorer.compute([
        ("machine learning", [0, 1]),
        ("machine learning", [3, 4]),
        ("deep learning", [6, 7]),
    ])
    by_text = scores_by_text(results)

    assert "machine learning" in by_text
    assert "deep learning" not in by_text
