import pytest
from typing import AsyncIterator, List, Dict
from unittest.mock import AsyncMock, patch
from termlint.extractors.cvalue import CValueExtractor  # assumed import

@pytest.fixture
def cvalue_extractor():
    return CValueExtractor(min_length=1, max_length=5, min_freq=1, threshold=0.0)

@pytest.fixture
def russian_text() -> str:
    return """Нейронные сети машинного обучения обрабатывают большие данные.
Искусственный интеллект использует глубокое обучение.
Машинное обучение - основа ИИ.
Глубокое обучение ускоряет обработку данных."""

@pytest.fixture
def english_text() -> str:
    return """Neural networks of machine learning process big data.
Artificial intelligence uses deep learning.
Machine learning is the basis of AI.
Deep learning accelerates data processing."""

@pytest.fixture
def simple_text() -> str:
    return "Machine learning neural networks."

@pytest.fixture
def expected_russian_candidates() -> List[Dict]:
    return [
        {"text": "нейронные сети", "score": pytest.approx(3.17), "freq": 1},
        {"text": "машинного обучения", "score": pytest.approx(2.32), "freq": 1},
        {"text": "искусственный интеллект", "score": pytest.approx(3.0), "freq": 1},
        {"text": "глубокое обучение", "score": pytest.approx(3.0), "freq": 2},
    ]

@pytest.fixture
def expected_english_candidates() -> List[Dict]:
    return [
        {"text": "neural networks", "score": pytest.approx(3.17), "freq": 1},
        {"text": "machine learning", "score": pytest.approx(2.32), "freq": 2},
        {"text": "artificial intelligence", "score": pytest.approx(3.0), "freq": 1},
        {"text": "deep learning", "score": pytest.approx(3.0), "freq": 2},
    ]

class TestCValueExtractor:
    async def test_basic_russian_extraction(self, cvalue_extractor, russian_text, expected_russian_candidates):
        """Test basic extraction on Russian text."""
        stream = cvalue_extractor.extract(russian_text)
        candidates = [entity async for entity in stream]
        assert len(candidates) >= len(expected_russian_candidates)
        # Check top candidates by score
        top_candidates = sorted(candidates[:10], key=lambda x: x.score, reverse=True)
        for i, expected in enumerate(expected_russian_candidates):
            assert top_candidates[i].text == expected["text"]
            assert top_candidates[i].score == pytest.approx(expected["score"], rel=0.1)
            assert top_candidates[i].extractortype == "cvalue"

    async def test_basic_english_extraction(self, cvalue_extractor, english_text, expected_english_candidates):
        """Test basic extraction on English text."""
        stream = cvalue_extractor.extract(english_text)
        candidates = [entity async for entity in stream]
        top_candidates = sorted(candidates[:10], key=lambda x: x.score, reverse=True)
        for i, expected in enumerate(expected_english_candidates):
            assert top_candidates[i].text == expected["text"]
            assert top_candidates[i].score == pytest.approx(expected["score"], rel=0.1)

    async def test_simple_extraction(self, cvalue_extractor, simple_text):
        """Test on simple text with nesting."""
        stream = cvalue_extractor.extract(simple_text)
        candidates = [entity async for entity in stream]
        assert any(c.text == "machine learning" for c in candidates)
        assert any(c.text == "neural networks" for c in candidates)

    async def test_nesting_calculation(self, cvalue_extractor):
        """Test C-Value calculation for nested terms."""
        nested_text = "deep neural networks learning"
        stream = cvalue_extractor.extract(nested_text)
        candidates = [entity async for entity in stream]

        deep_nn = next((c for c in candidates if c.text == "deep neural networks"), None)
        neural = next((c for c in candidates if c.text == "neural networks"), None)

        # Neural networks should have higher C-score due to frequency
        assert neural.score > deep_nn.score if deep_nn else True

    async def test_frequency_bias(self, cvalue_extractor):
        """Test frequency influence on score."""
        repeated_text = "machine learning machine learning AI"
        stream = cvalue_extractor.extract(repeated_text)
        candidates = [entity async for entity in stream]
        ml_score = next(c.score for c in candidates if c.text == "machine learning")
        ai_score = next(c.score for c in candidates if c.text == "AI")
        # High frequency increases score
        assert ml_score > ai_score

    async def test_length_filtering(self, russian_text):
        """Test filtering by min/max length."""
        short_extractor = CValueExtractor(min_length=3, max_length=3)
        stream = short_extractor.extract(russian_text)
        candidates = [entity async for entity in stream]
        assert all(3 <= len(entity.text.split()) <= 3 for entity in candidates)

    async def test_frequency_filtering(self, russian_text):
        """Test filtering by min_freq."""
        rare_extractor = CValueExtractor(min_freq=2)
        stream = rare_extractor.extract(russian_text)
        candidates = [entity async for entity in stream]
        assert all(c.freq >= 2 for c in candidates)

    async def test_score_threshold(self, russian_text):
        """Test score threshold."""
        strict_extractor = CValueExtractor(threshold=2.5)
        stream = strict_extractor.extract(russian_text)
        candidates = [entity async for entity in stream]
        assert all(c.score >= 2.5 for c in candidates)

    async def test_empty_text(self, cvalue_extractor):
        """Test on empty text."""
        stream = cvalue_extractor.extract("")
        candidates = [entity async for entity in stream]
        assert len(candidates) == 0

    async def test_single_word(self, cvalue_extractor):
        """Test on single word."""
        stream = cvalue_extractor.extract("ИИ")
        candidates = [entity async for entity in stream]
        assert len(candidates) == 1
        assert candidates[0].text == "ИИ"

    async def test_no_candidates(self, cvalue_extractor):
        """Test when no candidates above threshold."""
        strict_extractor = CValueExtractor(threshold=10.0)
        stream = strict_extractor.extract("simple text")
        candidates = [entity async for entity in stream]
        assert len(candidates) == 0

    def test_configurable_params(self):
        """Test configurable parameters."""
        extractor = CValueExtractor(min_length=2, max_length=4, min_freq=1, threshold=1.0)
        assert extractor.min_length == 2
        assert extractor.max_length == 4
        assert extractor.threshold == 1.0

    async def test_stream_is_async_iterator(self, cvalue_extractor, russian_text):
        """Test that stream is AsyncIterator[TextEntity]."""
        stream = cvalue_extractor.extract(russian_text)
        assert isinstance(stream, AsyncIterator)

# Edge cases
class TestEdgeCases:
    @pytest.mark.parametrize("text", [
        "a b c d e f",  # short words
        "ОченьДлинныйСоставнойТерминБезПробеловНаверноеНеТермин",  # camelcase
        "123 numbers only",  # numbers
    ])
    async def test_unlikely_candidates(self, cvalue_extractor, text):
        """Test unlikely candidates - should have low scores."""
        stream = cvalue_extractor.extract(text)
        candidates = [entity async for entity in stream]
        assert all(c.score < 2.0 for c in candidates[:5])  # low scores

    async def test_mixed_languages(self, cvalue_extractor):
        """Test mixed RU+EN text."""
        mixed = "Neural сети machine learning ИИ."
        stream = cvalue_extractor.extract(mixed)
        candidates = [entity async for entity in stream]
        assert len(candidates) > 0  # should work on mixed text
