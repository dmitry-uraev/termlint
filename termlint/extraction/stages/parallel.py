"""
Parallel processing stage for text entity extraction.
"""


import asyncio
from typing import AsyncIterator, Callable, List

from termlint.core.models import TextEntity
from termlint.core.types import Result, TextEntityStream


class ParallelStage:
    """Parallel processing stage for text entity extraction."""

    def __init__(self, extractors: List[Callable[[str], AsyncIterator[TextEntity]]]):
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

    async def _run_extractor(
            self, extractor: Callable[[str], AsyncIterator[TextEntity]],
            text: str
        ) -> List[TextEntity]:
        """Run an extractor and return a list of extracted entities."""
        iterator = extractor(text)
        return [entity async for entity in iterator]


async def example_main():
    """Docstring for example_main"""
    # TODO: add to tests

    async def rule_extractor(text: str) -> AsyncIterator[TextEntity]:
        await asyncio.sleep(0.1)  # Simulate processing delay
        yield TextEntity(
            text=text,
            original_text=text,
            lemma=text,
            span=(0, len(text)),
            score=0.8
        )

    async def cvalue_extractor(text: str) -> AsyncIterator[TextEntity]:
        await asyncio.sleep(0.1)  # Simulate processing delay
        yield TextEntity(
            text=text,
            original_text=text,
            lemma=text,
            span=(0, len(text)),
            score=0.7
        )

    parallel = ParallelStage([rule_extractor, cvalue_extractor])
    result = await parallel.extract("example text")

    if not result.is_ok:
        print(f"Error: {result.errors}")

    stream = result.value
    entities = await stream.to_list()
    print(entities.value)


if __name__ == "__main__":
    asyncio.run(example_main())
