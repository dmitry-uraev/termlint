import asyncio
import datetime
import json

from pathlib import Path
from typing import List

from termlint.core.models import Report


class JSONExporter:
    """
    Exports Report to JSON format.

    Supports all ReportType - serializes polymorphically.
    """

    async def export(self, report: Report, filepath: str | Path) -> Path:
        """
        Export single Report to JSON file.

        Args:
            report: Report to export
            filepath: Output file path

        Returns:
            Path to created file
        """
        filepath = Path(filepath).resolve()
        filepath.parent.mkdir(parents=True, exist_ok=True)

        enhanced_data = {
            "metadata": {
                "report_type": report.report_type.value,
                "timestamp": datetime.datetime.now().isoformat(),
                "termlint_version": "0.1.0", # TODO: pyproject.toml
            },
            "data": report.to_dict()
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._write_json(enhanced_data, filepath)
        )

        return filepath

    def _write_json(self, data: dict, filepath: Path):
        """Synchronous JSON write helper"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_multiple(self, reports: List[Report], output_dir: Path) -> List[Path]:
        """Exports multiple reports to separate files"""
        # TODO: implement multiple reports
        ...
