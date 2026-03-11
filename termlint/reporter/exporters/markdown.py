"""
TODO: Implement report conversion to Markdown
"""

from pathlib import Path

from termlint.core.models import Report


class MarkdownExporter:
    """
    Exports Report to Markdown format.

    Supports all ReportType - serializes polymorphically.
    """
    async def export(self, report: Report, filepath: str | Path) -> Path:
        ...

