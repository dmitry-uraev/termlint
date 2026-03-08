"""
Parallel processing stage for text entity extraction.
"""

import asyncio
from typing import AsyncIterator, List

from termlint.core.models import TextEntity
from termlint.core.stages import ProcessingStage
from termlint.core.types import Result, TextEntityStream
from termlint.extraction.extractors.base import BaseExtractor


class ParallelStage:
    """Parallel processing stage for text entity extraction."""

    def __init__(self, extractors: List[BaseExtractor]):
        self.extractors = extractors

    async def extract(self, text: str) -> Result[TextEntityStream]:
        """Run all extractors in parallel and combine results into a single TextEntityStream."""
        # create coroutines for each extractor
        tasks = [
            self._run_extractor(extractor, text)
            for extractor in self.extractors
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        failed = [r for r in results if isinstance(r, Exception)]
        if failed:
            return Result.err([f"Extractor failed: {e}" for e in failed])

        # get all results from successful extractors
        async def extract_from_results() -> AsyncIterator[TextEntity]:
            for result in results:
                if isinstance(result, list):  # List[TextEntity]
                    for entity in result:
                        yield entity

        return Result.ok(TextEntityStream(extract_from_results()))

    async def _run_extractor(self, extractor: BaseExtractor, text: str) -> List[TextEntity]:
        """Run an extractor and return a list of extracted entities."""
        entities = []
        # TODO: pylance, why?, make public
        async for entity in extractor._extract(text): #type:ignore
            entities.append(entity)
        return entities


class ParallelExtractionStage(ProcessingStage[str, TextEntityStream]):
    """Adapter ParallelStage → ProcessingStage"""

    def __init__(self, extractors: List[BaseExtractor]):
        self._parallel_stage = ParallelStage(extractors)

    async def process(self, text: str) -> Result[TextEntityStream]:
        return await self._parallel_stage.extract(text)


async def example_main():
    """Docstring for example_main"""
    # TODO: add to tests

    from termlint.extraction.extractors.rule import RuleExtractor

    text = """
    Нейронные сети машинного обучения обрабатывают большие данные.
    Искусственный интеллект использует глубокое обучение.
    """

    extractor = RuleExtractor(model='ru_core_news_sm')
    print("direct _extract()")
    count = 0
    async for entity in extractor._extract(text):
        print(f"  {count}. '{entity.text}'")
        count += 1
    print(f"_extract(): {count} entities\n")

    # TODO: direct __call__ seems not working
    print("extractor(text)")
    count = 0
    async for entity in extractor(text):
        print(f"  {count}. '{entity.text}'")
        count += 1
    print(f"extractor(text): {count} entities\n")


if __name__ == "__main__":
    asyncio.run(example_main())
