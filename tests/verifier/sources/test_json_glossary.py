import json
import asyncio
import pytest

from pathlib import Path
from termlint.verifier.sources.json_glossary import JSONGlossarySource
from termlint.constants import TESTS_DIR


@pytest.fixture
def sample_json_glossary(tmp_path):
    glossary = tmp_path / "glossary.json"

    data = [
        {
            "id": "db:001",
            "label": "database",
            "synonyms": ["db", "data base"],
            "definition": "A structured set of data held in a computer, especially one that is accessible in various ways.",
        }
    ]
    glossary.write_text(json.dumps(data), encoding='utf-8')
    return glossary


@pytest.fixture
def full_ml_it_glossary(tmp_path: Path):
    """Test glossary for IT/ML/Dev (13 terms)"""
    glossary_path = tmp_path / "full_ml_it_glossary.json"

    data = [
        {"id": "ml:001", "label": "нейронная сеть", "synonyms": ["neural network", "нейросеть", "NN"]},
        {"id": "ml:002", "label": "свёрточная нейронная сеть", "synonyms": ["CNN", "convolutional neural network"]},
        {"id": "ml:003", "label": "рекуррентная нейронная сеть", "synonyms": ["RNN"]},
        {"id": "ml:004", "label": "трансформер", "synonyms": ["Transformer"]},
        {"id": "dev:001", "label": "микросервис", "synonyms": ["microservice"]},
        {"id": "dev:002", "label": "монолит", "synonyms": ["monolith"]},
        {"id": "dev:003", "label": "Docker", "synonyms": ["контейнер"]},
        {"id": "dev:004", "label": "CI/CD", "synonyms": ["непрерывная доставка"]},
        {"id": "dev:005", "label": "REST API", "synonyms": ["RESTful API"]},
        {"id": "dev:006", "label": "GraphQL", "synonyms": []},
        {"id": "it:001", "label": "Kubernetes", "synonyms": ["K8s"]},
        {"id": "ml:010", "label": "машинное обучение", "synonyms": ["machine learning", "ML"]},
        {"id": "ml:011", "label": "искусственный интеллект", "synonyms": ["AI", "ИИ"]}
    ]

    glossary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return glossary_path


@pytest.fixture
def initialized_json_glossary(full_ml_it_glossary: Path):
    """Initializes JSONGlossarySource from full_ml_it_glossary"""
    source = JSONGlossarySource(full_ml_it_glossary)
    result = asyncio.run(source.initialize())  # Синхронно для fixture
    assert result.is_ok, f"Failed to initialize: {result.errors}"
    return source


async def test_glossary_ideal():
    glossary = TESTS_DIR / 'fixtures' / 'test_glossary.json'

    if glossary.exists():
        source = JSONGlossarySource(glossary)
        result = await source.initialize()
        assert result.is_ok
        assert len(source._entities) == 13


async def test_json_glossary_loads(sample_json_glossary):
    source = JSONGlossarySource(sample_json_glossary)
    result = await source.initialize()

    assert result.is_ok, f"Initialization failed: {result.errors}"
    entity = await source.get_entity("database")
    assert entity.is_ok, f"Entity lookup failed: {entity.errors}"
    assert entity.value.label == "database"


class TestJSONGlossarySource:

    async def test_full_ml_glossary_loading(self, full_ml_it_glossary):
        """Check full glossary file loading"""
        source = JSONGlossarySource(full_ml_it_glossary)
        result = await source.initialize()

        assert result.is_ok
        assert len(source._entities) == 13, "Should load 13 entities"

    async def test_ml_term_lookup(self, initialized_json_glossary):
        """Search ML terms"""
        source = initialized_json_glossary

        tests = [
            ("нейронная сеть", "ml:001"),
            ("neural network", "ml:001"),
            ("CNN", "ml:002"),
            ("микросервис", "dev:001"),
            ("Docker", "dev:003"),
            ("Kubernetes", "it:001")
        ]

        for term, expected_id in tests:
            entity = await source.get_entity(term)
            assert entity.is_ok, f"'{term}' not found"
            assert entity.value.id == expected_id, f"Wrong ID for '{term}'"

    async def test_batch_lookup(self, initialized_json_glossary):
        """Batch term search"""
        source = initialized_json_glossary
        terms = ["нейронная сеть", "Docker", "неизвестный_термин"]

        result = await source.get_entities(terms)
        assert result.is_ok
        assert len(result.value) == 2
        assert result.value[0].id == "ml:001"

    async def test_missing_file_error(self, tmp_path):
        """Error if file is missing"""
        missing_path = tmp_path / "missing.json"
        source = JSONGlossarySource(missing_path)
        result = await source.initialize()

        assert not result.is_ok
        assert "not found" in result.errors[0]

    async def test_invalid_json_error(self, tmp_path):
        """Error for incorrect JSON"""
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("not json", encoding='utf-8')

        source = JSONGlossarySource(invalid_path)
        result = await source.initialize()

        assert not result.is_ok
        assert "Invalid JSON" in result.errors[0]
