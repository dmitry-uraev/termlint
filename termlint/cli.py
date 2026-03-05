"""Command-line interface for termlint."""

import asyncio
import logging
from enum import IntEnum
from pathlib import Path
from typing import List, Optional, Union

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from termlint.config import TermlintConfig
from termlint.core.models import Report, ReportType
from termlint.pipeline import UnifiedPipeline

from termlint.utils.logger import get_child_logger, setup_root_logger


logger = get_child_logger("cli")
console = Console()
pass_config = click.make_pass_decorator(dict, ensure=True)


class ExitCode(IntEnum):
    OK = 0
    QUALITY_GATE_FAIL = 1
    USAGE_OR_CONFIG_ERROR = 2
    INTERNAL_PIPELINE_ERROR = 3


@click.group()
@click.version_option(package_name="termlint")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v: INFO, -vv: DEBUG)")
@click.option("-q", "--quiet", count=True, help="Decrease verbosity (-q: ERROR, -qq: CRITICAL)")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to pyproject.toml with [tool.termlint] settings",
)
@click.option(
    "--log-level",
    type=click.Choice(["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False),
    help="Override log level",
)
@click.option("--log-file", type=click.Path(path_type=Path), help="Write logs to a file")
@pass_config
def cli(
    ctx,
    verbose: int,
    quiet: int,
    config_path: Optional[Path],
    log_level: Optional[str],
    log_file: Optional[Path],
):
    """Terminology linter for docs"""
    try:
        config = TermlintConfig.from_pyproject(config_path or Path("pyproject.toml"))
    except Exception as exc:
        click.echo(f"Error: Failed to load config: {exc}", err=True)
        raise click.exceptions.Exit(ExitCode.USAGE_OR_CONFIG_ERROR) from exc
    setup_root_logger(
        level=resolve_logging_level(
            config.logging.level,
            verbose=verbose,
            quiet=quiet,
            explicit_level=log_level,
        ),
        log_file=log_file or config.logging.log_file,
        fmt=config.logging.fmt,
        datefmt=config.logging.datefmt,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
        force=True,
    )
    ctx['config'] = config

@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option('--source', type=click.Path(exists=True, path_type=Path), required=True, help='📚 Glossary file')
@click.option('--verifier', type=click.Choice(["exact", "fuzzy"]), help="Verifier type")
@click.option("--threshold", type=int, help="🎯 Fuzzy threshold")
@click.option("--output-dir", type=click.Path(file_okay=False, path_type=Path), help="📁 Output directory")
@pass_config
def verify(
    ctx,
    files: Union[Path, tuple[Path, ...], List[Path]],
    source: Path,
    verifier: Optional[str],
    threshold: Optional[int],
    output_dir: Optional[Path]
):
    """Full verification pipeline (default)"""

    async def run_pipeline():

        # CLI overrides
        config = ctx['config']
        config.verifier.source = Path(source)
        if verifier:
            config.verifier.type = verifier
        if threshold:
            config.verifier.fuzzy["threshold"] = threshold
        if output_dir:
            config.output_dir = output_dir

        pipeline = await build_pipeline_or_exit(config)
        file_list = normalize_files(files)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            overall_task = progress.add_task("[bold]Files[/bold]", total=len(file_list))
            current_task = progress.add_task("Waiting...", total=1)
            all_reports = []
            for file_path in file_list:
                progress.update(current_task, description=f"📄 {file_path.name}", total=1, completed=0)

                def on_step(step: int, total: int, stage_name: str):
                    progress.update(
                        current_task,
                        description=f"📄 {file_path.name} • {stage_name}",
                        total=total,
                        completed=max(step - 1, 0),
                    )

                result = await run_pipeline_for_file_or_exit(
                    pipeline,
                    file_path,
                    progress_callback=on_step
                )
                progress.update(current_task, completed=progress.tasks[current_task].total, description=f"✅ {file_path.name}")
                progress.advance(overall_task, 1)

                if not result.is_ok:
                    console.print(f"[red]❌ Failed[/red] {file_path}: {result.errors}")
                    raise click.exceptions.Exit(ExitCode.INTERNAL_PIPELINE_ERROR)

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
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--output-dir", type=click.Path(file_okay=False, path_type=Path), help="📁 Output directory")
@pass_config
def extract(
    ctx,
    files: Union[Path, tuple[Path, ...], List[Path]],
    output_dir: Optional[Path]
):
    """Extract terms only"""

    async def run_pipeline():
        config = ctx['config']
        if output_dir:
            config.output_dir = output_dir

        config.reports.include = [ReportType.EXTRACTION]
        config.pipeline.stages = ["extract", "report"]

        pipeline = await build_pipeline_or_exit(config)
        file_list = normalize_files(files)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            overall_task = progress.add_task("[bold]Files[/bold]", total=len(file_list))
            current_task = progress.add_task("Waiting...", total=1)
            for file_path in file_list:
                progress.update(current_task, description=f"🔍 {file_path.name}", total=1, completed=0)

                def on_step(step: int, total: int, stage_name: str):
                    progress.update(
                        current_task,
                        description=f"🔍 {file_path.name} • {stage_name}",
                        total=total,
                        completed=max(step - 1, 0),
                    )

                result = await run_pipeline_for_file_or_exit(
                    pipeline,
                    file_path,
                    progress_callback=on_step
                )
                progress.update(current_task, completed=progress.tasks[current_task].total, description=f"✅ {file_path.name}")
                progress.advance(overall_task, 1)

                if not result.is_ok:
                    console.print(f"[red]❌ {result.errors}[/red]")
                    raise click.exceptions.Exit(ExitCode.INTERNAL_PIPELINE_ERROR)

                extraction_report = next((r for r in result.value if isinstance(r, Report) and r.report_type == "extraction"), None)
                if extraction_report:
                    console.print(f"✅ [green]Extracted {extraction_report.processed_items} terms → {config.output_dir / 'extraction.json'}[/green]")

    asyncio.run(run_pipeline())

@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option('--source', type=click.Path(exists=True, path_type=Path), required=True, help='📚 Glossary file')
@pass_config
def ci(
    ctx,
    files: Union[Path, tuple[Path, ...], List[Path]],
    source: Path
):
    """CI/CD quality gates only"""

    async def run_pipeline():
        config = ctx['config']
        config.verifier.source = Path(source)
        config.reports.include = [ReportType.VERIFICATION, ReportType.QUALITY_GATE]

        failed_files = []

        pipeline = await build_pipeline_or_exit(config)
        file_list = normalize_files(files)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            overall_task = progress.add_task("[bold]Files[/bold]", total=len(file_list))
            current_task = progress.add_task("Waiting...", total=1)
            for file_path in file_list:
                progress.update(current_task, description=f"🧪 {file_path.name}", total=1, completed=0)

                def on_step(step: int, total: int, stage_name: str):
                    progress.update(
                        current_task,
                        description=f"🧪 {file_path.name} • {stage_name}",
                        total=total,
                        completed=max(step - 1, 0),
                    )

                result = await run_pipeline_for_file_or_exit(
                    pipeline,
                    file_path,
                    progress_callback=on_step
                )
                progress.update(current_task, completed=progress.tasks[current_task].total, description=f"✅ {file_path.name}")
                progress.advance(overall_task, 1)
                if not result.is_ok:
                    console.print(f"[red]❌ Pipeline error[/red]: {result.errors}")
                    raise click.exceptions.Exit(ExitCode.INTERNAL_PIPELINE_ERROR)

                quality_report = next((r for r in result.value if isinstance(r, Report) and r.report_type == ReportType.QUALITY_GATE), None)
                if quality_report and not quality_report.quality_pass:
                    console.print(f"[red bold]❌ {file_path.name}: Quality gate failed ({quality_report.processed_items}/{quality_report.total_items})[/red bold]")
                    failed_files.append(file_path)

        if failed_files:
            console.print(f"\n💥 [red bold]{len(failed_files)}/{len(file_list)} files failed quality gates[/red bold]")
            raise click.exceptions.Exit(ExitCode.QUALITY_GATE_FAIL)

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
        raise click.exceptions.Exit(ExitCode.USAGE_OR_CONFIG_ERROR)

    console.print("✅ [green bold]Configuration is valid![/green bold]")
    console.print(f"📋 Pipeline: {', '.join(config.pipeline.stages)}")


def normalize_files(files: Union[Path, tuple, List]) -> List[Path]:
    """Path → List[Path]"""
    return [files] if isinstance(files, Path) else list(files)


def resolve_logging_level(
    config_level: str,
    verbose: int,
    quiet: int,
    explicit_level: Optional[str],
) -> int:
    """Resolve logging level precedence: explicit > quiet > verbose > config."""
    if explicit_level:
        return level_name_to_int(explicit_level)

    if quiet >= 2:
        return logging.CRITICAL
    if quiet == 1:
        return logging.ERROR

    if verbose >= 2:
        return logging.DEBUG
    if verbose == 1:
        return logging.INFO

    return level_name_to_int(config_level)


def level_name_to_int(level_name: str) -> int:
    """Convert standard logging level name to numeric value."""
    return getattr(logging, level_name.upper(), logging.WARNING)


async def build_pipeline_or_exit(config: TermlintConfig) -> UnifiedPipeline:
    """Build pipeline and convert setup exceptions to clean CLI errors."""
    try:
        return await UnifiedPipeline.from_config(config)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]❌ Configuration error[/red]: {exc}")
        raise click.exceptions.Exit(ExitCode.USAGE_OR_CONFIG_ERROR) from exc
    except NotImplementedError as exc:
        console.print(f"[red]❌ Unsupported configuration[/red]: {exc}")
        raise click.exceptions.Exit(ExitCode.USAGE_OR_CONFIG_ERROR) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unexpected failure while building pipeline")
        console.print("[red]❌ Internal error while preparing pipeline[/red]")
        raise click.exceptions.Exit(ExitCode.INTERNAL_PIPELINE_ERROR) from exc


async def run_pipeline_for_file_or_exit(
    pipeline: UnifiedPipeline,
    file_path: Path,
    progress_callback,
):
    """Run pipeline for one file and convert runtime exceptions to clean CLI errors."""
    try:
        return await pipeline.run_and_collect(
            file_path.read_text(encoding='utf-8'),
            progress_callback=progress_callback
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unexpected failure while processing file '%s'", file_path)
        console.print(f"[red]❌ Internal error while processing[/red] {file_path}")
        raise click.exceptions.Exit(ExitCode.INTERNAL_PIPELINE_ERROR) from exc


if __name__ == "__main__":
    cli()
