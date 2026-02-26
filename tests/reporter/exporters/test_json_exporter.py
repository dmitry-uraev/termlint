import json

from termlint.core.models import Report, ReportType
from termlint.reporter.exporters.json import JSONExporter


async def test_json_exporter_ideal(tmp_path, sample_text_entity):
    report = Report(
        report_type=ReportType.VERIFICATION,
        total_items=100,
        processed_items=100,
        coverage_pct=95.,
        unknown_terms=[sample_text_entity]
    )

    exporter = JSONExporter()
    filename = "test-report.json"
    path = tmp_path / filename

    result_path = await exporter.export(report, path)

    assert result_path == path.resolve()
    assert path.exists()
    assert path.stat().st_size > 100  # Non-empty file

    # Validate JSON content
    with open(path, 'r') as f:
        data = json.load(f)
        assert data["metadata"]["report_type"] == "verification"
        assert data["data"]["coverage_pct"] == 95.0
