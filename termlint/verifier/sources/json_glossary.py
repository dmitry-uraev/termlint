"""JSON-based glossary source"""

import json
from pathlib import Path
from typing import List, Dict

from termlint.core.types import Result
from termlint.core.models import Entity
from termlint.verifier.sources.base import KnowledgeSource
from termlint.utils.logger import get_child_logger


logger = get_child_logger('GlossarySource (JSON)')


class JSONGlossarySource(KnowledgeSource):
    """Knowledge source that loads entities from a JSON glossary file"""

    def __init__(self, path: Path | str):
        super().__init__()  # initialize index
        self.path = Path(path)
        self._entities: List[Entity] = []

    async def initialize(self) -> Result[None]:
        """Asynchronously load from JSON file (lazy initialization)"""
        try:
            if not self.path.exists():
                logger.warning(f"Glossary file not found: {self.path}")
                return Result.err([f"Glossary file not found: {self.path}"])

            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._entities = [Entity(**item) for item in data]
            logger.info(f"Extracted {len(self._entities)} entities")
            self._build_index()
            return Result.ok(None)

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {self.path}: {e}")
            return Result.err([f"Invalid JSON in {self.path}: {e}"])
        except Exception as e:
            logger.warning(f"Failed to load glossary: {e}")
            return Result.err([f"Failed to load glossary: {e}"])

    def _build_index(self) -> None:
        """Build search index (label + synonyms)"""
        logger.info(f"Building index")
        self._index.clear()
        for entity in self._entities:
            terms = [entity.label] + entity.synonyms
            for term in terms:
                if term.lower() not in self._index:
                    self._index[term.lower()] = []
                self._index[term.lower()].append(entity)
        logger.info(f"Built index with {len(self._index)} entries")

    async def get_entity(self, term: str) -> Result[Entity]:
        """Find single term (exact match) and return its entity representation"""
        matches = self._index.get(term.lower(), [])
        if matches:
            return Result.ok(matches[0])  # Return first match for simplicity
        else:
            logger.info(f"Term not found: '{term}'")
            return Result.err([f"Term not found: '{term}'"])

    async def get_entities(self, terms: List[str]) -> Result[List[Entity]]:
        """Batch lookup for multiple terms"""
        results = []
        for term in terms:
            entity_result = await self.get_entity(term)
            if entity_result.is_ok:
                results.append(entity_result.value)
        logger.info(f"Found {len(results)} matches in ontology")
        return Result.ok(results)

    async def close(self) -> None:
        """No resources to close for file-based source"""
        pass


async def test_main():
    from termlint.constants import TESTS_DIR
    source = JSONGlossarySource(TESTS_DIR / 'fixtures' / 'test_glossary.json')
    await source.initialize()

    result = await source.get_entity('Kubernetes')

    if result.is_ok:
        print(result.value)
    else:
        print(result.errors)


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_main())
