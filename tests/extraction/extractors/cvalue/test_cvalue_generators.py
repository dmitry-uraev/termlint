from termlint.extraction.extractors.cvalue_support.candidate_generators import (
    HeuristicCandidateGenerator,
    SpacyCandidateGenerator,
)


def make_token_info(tokens, *, sent_id=0, pos=None, stopwords=None, punct=None):
    """Build minimal token metadata for generator tests.

    Args:
        tokens: Token texts in order.
        sent_id: Sentence id to assign to all tokens by default.
        pos: Optional list of POS tags. If omitted, all values are None.
        stopwords: Optional set of lowercase lemmas treated as stop words.
        punct: Optional set of token indices marked as punctuation.

    Returns:
        A list of token metadata dictionaries compatible with candidate generators.
    """
    stopwords = stopwords or set()
    punct = punct or set()
    pos = pos or [None] * len(tokens)

    return [
        {
            "token": token,
            "lemma": token.lower(),
            "pos": pos[i],
            "char_start": i * 10,
            "char_end": i * 10 + len(token),
            "sent_id": sent_id,
            "is_stop": token.lower() in stopwords,
            "is_punct": i in punct,
        }
        for i, token in enumerate(tokens)
    ]


def candidate_texts(candidates):
    """Return candidate texts only, preserving duplicates if any."""
    return [text for text, _ in candidates]


def candidate_map(candidates):
    """Return mapping text -> indices for easier assertions."""
    return {text: indices for text, indices in candidates}


# ---------------------------------------------------------------------------
# Heuristic generator tests
# ---------------------------------------------------------------------------

def test_heuristic_generator_keeps_clean_bigrams():
    tokens = ["machine", "learning", "systems"]
    token_info = make_token_info(tokens)

    generator = HeuristicCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "machine learning" in texts
    assert "learning systems" in texts
    assert "machine learning systems" not in texts  # heuristic mode is capped


def test_heuristic_generator_rejects_candidates_with_stopwords():
    tokens = ["neural", "networks", "and", "learning"]
    token_info = make_token_info(tokens, stopwords={"and"})

    generator = HeuristicCandidateGenerator(min_length=2, max_length=3)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "neural networks" in texts
    assert "networks and" not in texts
    assert "and learning" not in texts
    assert "neural networks and" not in texts


def test_heuristic_generator_rejects_bad_english_endings():
    tokens = ["artificial", "intelligence", "uses", "learning"]
    token_info = make_token_info(tokens)

    generator = HeuristicCandidateGenerator(min_length=2, max_length=3)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  #type:ignore
    texts = candidate_texts(candidates)

    assert "artificial intelligence" in texts
    assert "intelligence uses" not in texts


def test_heuristic_generator_rejects_excessive_title_case():
    tokens = ["Neural", "Networks", "Methods", "Models"]
    token_info = make_token_info(tokens)

    generator = HeuristicCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  #type:ignore
    texts = candidate_texts(candidates)

    assert "Neural Networks" in texts
    assert "Networks Methods" in texts
    assert "Neural Networks Methods" not in texts
    assert "Networks Methods Models" not in texts


def test_heuristic_generator_respects_sentence_boundaries():
    tokens = ["machine", "learning", "deep", "learning"]
    token_info = [
        {
            "token": "machine",
            "lemma": "machine",
            "pos": None,
            "char_start": 0,
            "char_end": 7,
            "sent_id": 0,
            "is_stop": False,
            "is_punct": False,
        },
        {
            "token": "learning",
            "lemma": "learning",
            "pos": None,
            "char_start": 8,
            "char_end": 16,
            "sent_id": 0,
            "is_stop": False,
            "is_punct": False,
        },
        {
            "token": "deep",
            "lemma": "deep",
            "pos": None,
            "char_start": 18,
            "char_end": 22,
            "sent_id": 1,
            "is_stop": False,
            "is_punct": False,
        },
        {
            "token": "learning",
            "lemma": "learning",
            "pos": None,
            "char_start": 23,
            "char_end": 31,
            "sent_id": 1,
            "is_stop": False,
            "is_punct": False,
        },
    ]

    generator = HeuristicCandidateGenerator(min_length=2, max_length=3)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "machine learning" in texts
    assert "deep learning" in texts
    assert "learning deep" not in texts


# ---------------------------------------------------------------------------
# spaCy-like generator tests
# ---------------------------------------------------------------------------

def test_spacy_generator_extracts_adj_noun_candidate():
    tokens = ["deep", "learning"]
    token_info = make_token_info(tokens, pos=["ADJ", "NOUN"])

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "deep learning" in texts


def test_spacy_generator_extracts_adj_noun_noun_candidate():
    tokens = ["machine", "learning", "methods"]
    token_info = make_token_info(tokens, pos=["ADJ", "NOUN", "NOUN"])

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "machine learning" in texts
    assert "machine learning methods" in texts
    assert "learning methods" in texts


def test_spacy_generator_rejects_noun_adj_noun_sequence():
    tokens = ["intelligence", "deep", "learning"]
    token_info = make_token_info(tokens, pos=["NOUN", "ADJ", "NOUN"])

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "intelligence deep" not in texts
    assert "deep learning" in texts
    assert "intelligence deep learning" not in texts


def test_spacy_generator_stops_at_boundary_tokens():
    tokens = ["artificial", "intelligence", "uses", "deep", "learning"]
    token_info = make_token_info(tokens, pos=["ADJ", "NOUN", "VERB", "ADJ", "NOUN"])

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "artificial intelligence" in texts
    assert "deep learning" in texts
    assert "intelligence uses" not in texts
    assert "artificial intelligence uses deep" not in texts


def test_spacy_generator_respects_sentence_boundaries():
    tokens = ["neural", "networks", "deep", "learning"]
    token_info = [
        {
            "token": "neural",
            "lemma": "neural",
            "pos": "ADJ",
            "char_start": 0,
            "char_end": 6,
            "sent_id": 0,
            "is_stop": False,
            "is_punct": False,
        },
        {
            "token": "networks",
            "lemma": "network",
            "pos": "NOUN",
            "char_start": 7,
            "char_end": 15,
            "sent_id": 0,
            "is_stop": False,
            "is_punct": False,
        },
        {
            "token": "deep",
            "lemma": "deep",
            "pos": "ADJ",
            "char_start": 17,
            "char_end": 21,
            "sent_id": 1,
            "is_stop": False,
            "is_punct": False,
        },
        {
            "token": "learning",
            "lemma": "learning",
            "pos": "NOUN",
            "char_start": 22,
            "char_end": 30,
            "sent_id": 1,
            "is_stop": False,
            "is_punct": False,
        },
    ]

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    texts = candidate_texts(candidates)

    assert "neural networks" in texts
    assert "deep learning" in texts
    assert "networks deep" not in texts


def test_spacy_generator_rejects_candidate_without_noun_head():
    tokens = ["deep", "neural"]
    token_info = make_token_info(tokens, pos=["ADJ", "ADJ"])

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore

    assert candidates == []


def test_spacy_generator_rejects_candidate_ending_with_adjective():
    tokens = ["learning", "deep"]
    token_info = make_token_info(tokens, pos=["NOUN", "ADJ"])

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore

    assert candidates == []


def test_spacy_generator_keeps_original_token_indices():
    tokens = ["artificial", "intelligence", "uses", "deep", "learning"]
    token_info = make_token_info(tokens, pos=["ADJ", "NOUN", "VERB", "ADJ", "NOUN"])

    generator = SpacyCandidateGenerator(min_length=2, max_length=4)
    candidates = generator.generate(tokens=tokens, token_info=token_info)  # type:ignore
    cmap = candidate_map(candidates)

    assert cmap["artificial intelligence"] == [0, 1]
    assert cmap["deep learning"] == [3, 4]
