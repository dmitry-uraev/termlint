import pytest
import json
import asyncio

from pathlib import Path

from termlint.verifier.sources.json_glossary import JSONGlossarySource


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
