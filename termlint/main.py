import asyncio
import logging

from termlint.config import TermlintConfig
from termlint.pipeline import UnifiedPipeline
from termlint.utils.logger import setup_root_logger

async def main():
    """Termlint entrypoint"""

    text = """
    Нейронные сети машинного обучения обрабатывают большие данные.
    Искусственный интеллект использует глубокое обучение.
    """

    config = TermlintConfig.from_pyproject()
    setup_root_logger(
        level=getattr(logging, config.logging.level.upper(), logging.WARNING),
        log_file=config.logging.log_file,
        fmt=config.logging.fmt,
        datefmt=config.logging.datefmt,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
        force=True,
    )
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
