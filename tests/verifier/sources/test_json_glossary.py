from termlint.verifier.sources.json_glossary import JSONGlossarySource
from termlint.constants import TESTS_DIR


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
