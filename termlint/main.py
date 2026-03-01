import asyncio

from termlint.config import TermlintConfig
from termlint.pipeline import UnifiedPipeline

async def main():
    """Termlint entrypoint"""

    text = """
    Нейронные сети машинного обучения обрабатывают большие данные.
    Искусственный интеллект использует глубокое обучение.
    """

    config = TermlintConfig.from_pyproject()
    pipeline = await UnifiedPipeline.from_config(config)

    result = await pipeline.run_and_collect(text)

    if result.is_ok:
        print(f"Success: {len(result.value)} items processed")
        for item in result.value:
            print(f"  - {item}")
    else:
        print(f"Failed: {result.errors}")


if __name__ == "__main__":
    asyncio.run(main())
