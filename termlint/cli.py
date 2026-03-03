"""Command-line interface for termlint."""

import asyncio
from pathlib import Path
from typing import List, Optional, Union

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from termlint.config import TermlintConfig
from termlint.core.models import Report, ReportType
from termlint.pipeline import UnifiedPipeline

from termlint.utils.logger import get_child_logger


logger = get_child_logger("cli")
console = Console()
pass_config = click.make_pass_decorator(dict, ensure=True)


@click.group()
@click.version_option(package_name="termlint")
@pass_config
def cli(ctx):
    """Terminology linter for docs"""
    ctx['config'] = TermlintConfig.from_pyproject()

@cli.command()
@click.argument('files', nargs=1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option('--source', type=click.Path(exists=True, path_type=Path), help='📚 Glossary file')
@click.option('--verifier', type=click.Choice(["exact", "fuzzy"]), help="Verifier type")
@click.option("--threshold", type=int, help="🎯 Fuzzy threshold")
@click.option("--output-dir", type=click.Path(file_okay=False, path_type=Path), help="📁 Output directory")
@pass_config
def verify(
    ctx,
    files: Union[Path, List[Path]],
    source: Optional[Path],
    verifier: Optional[str],
    threshold: Optional[int],
    output_dir: Optional[Path]
):
    """Full verification pipeline (default)"""

    async def run_pipeline():

        # CLI overrides
        config = ctx['config']
        if source:
            config.verifier.source = Path(source)
        if verifier:
            config.verifier.type = verifier
        if threshold:
            config.verifier.fuzzy["threshold"] = threshold
        if output_dir:
            config.output_dir = output_dir

        pipeline = await UnifiedPipeline.from_config(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            all_reports = []
            for file_path in normalize_files(files):
                task = progress.add_task(f"📄 {file_path.name}", total=None)

                result = await pipeline.run_and_collect(file_path.read_text(encoding='utf-8'))
                progress.remove_task(task)

                if not result.is_ok:
                    console.print(f"[red]❌ Failed[/red] {file_path}: {result.errors}")
                    raise click.Abort()

                reports = result.value
                all_reports.extend(reports)

        # print summary
        verification = next((r for r in all_reports if r.report_type == ReportType.VERIFICATION), None)
        if verification:
            color = "green" if verification.coverage_pct >= 90 else "yellow"
            console.print(f"📊 [bold {color}]Coverage: {verification.coverage_pct:.1f}%[/bold {color}] ({verification.processed_items}/{verification.total_items})")

        quality = next((r for r in all_reports if r.report_type == ReportType.QUALITY_GATE), None)
        if quality and not quality.quality_pass:
            console.print(f"⚠️  [yellow]Quality Gate would FAIL in CI mode[/yellow]")

    asyncio.run(run_pipeline())

@cli.command()
@click.argument("files", nargs=1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--output-dir", type=click.Path(file_okay=False, path_type=Path), help="📁 Output directory")
@pass_config
def extract(
    ctx,
    files: Union[Path, List[Path]],
    output_dir: Optional[Path]
):
    """Extract terms only"""

    async def run_pipeline():
        config = ctx['config']
        if output_dir:
            config.output_dir = output_dir

        config.reports.include = [ReportType.EXTRACTION]
        config.pipeline.stages = ["extract", "report"]

        pipeline = await UnifiedPipeline.from_config(config)

        with Progress(console=console) as progress:
            for file_path in normalize_files(files):
                task = progress.add_task(f"🔍 Extracting {file_path.name}", total=None)

                result = await pipeline.run_and_collect(file_path.read_text(encoding='utf-8'))
                progress.remove_task(task)

                if not result.is_ok:
                    console.print(f"[red]❌ {result.errors}[/red]")
                    raise click.Abort()

                extraction_report = next((r for r in result.value if isinstance(r, Report) and r.report_type == "extraction"), None)
                if extraction_report:
                    console.print(f"✅ [green]Extracted {extraction_report.processed_items} terms → {config.output_dir / 'extraction.json'}[/green]")

    asyncio.run(run_pipeline())

@cli.command()
@click.argument("files", nargs=1, type=click.Path(exists=True, path_type=Path), required=True)
@pass_config
def ci(
    ctx,
    files: Union[Path, List[Path]]
):
    """CI/CD quality gates only"""

    async def run_pipeline():
        config = ctx['config']
        config.reports.include = [ReportType.VERIFICATION, ReportType.QUALITY_GATE]

        failed_files = []

        pipeline = await UnifiedPipeline.from_config(config)

        with Progress(console=console) as progress:
            for file_path in normalize_files(files):
                task = progress.add_task(f"🧪 Testing {file_path.name}", total=None)

                result = await pipeline.run_and_collect(file_path.read_text(encoding='utf-8'))
                progress.remove_task(task)
                if not result.is_ok:
                    console.print(f"[red]❌ Pipeline error[/red]: {result.errors}")
                    raise click.Abort(3)

                quality_report = next((r for r in result.value if isinstance(r, Report) and r.report_type == ReportType.QUALITY_GATE), None)
                if quality_report and not quality_report.quality_pass:
                    console.print(f"[red bold]❌ {file_path.name}: Quality gate failed ({quality_report.processed_items}/{quality_report.total_items})[/red bold]")
                    failed_files.append(file_path)

        if failed_files:
            console.print(f"\n💥 [red bold]{len(failed_files)}/{len(normalize_files(files))} files failed quality gates[/red bold]")
            raise click.Abort(1)

    asyncio.run(run_pipeline())

@cli.command()
@pass_config
def config(ctx: dict):
    """Show effective configuration"""
    config = ctx['config']
    console.print("[bold cyan]Effective termlint configuration:[/bold cyan]")
    console.print(config.model_dump_json(indent=2))

@cli.command()
@pass_config
def validate(ctx: dict):
    """Validate configuration"""

    config = ctx['config']

    issues = []
    if not config.pipeline.stages:
        issues.append("No pipeline stages configured")

    if config.verifier.source and not config.verifier.source.exists():
        issues.append(f"Glossary not found: {config.verifier.source}")

    if issues:
        console.print("❌ [red bold]Configuration issues:[/red bold]")
        for issue in issues:
            console.print(f"  • {issue}")
        raise click.Abort(3)

    console.print("✅ [green bold]Configuration is valid![/green bold]")
    console.print(f"📋 Pipeline: {', '.join(config.pipeline.stages)}")


def normalize_files(files: Union[Path, List]) -> List[Path]:
    """Path → List[Path]"""
    return [files] if isinstance(files, Path) else list(files)


if __name__ == "__main__":
    cli()
