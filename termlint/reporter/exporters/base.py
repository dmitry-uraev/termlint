from pathlib import Path
from typing import Protocol

from termlint.core.models import Report


class Exporter(Protocol):
    """Base exporter interface"""
    async def export(self, report: Report, filepath: str | Path) -> Path:
        ...
