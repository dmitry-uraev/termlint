# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows
[PEP 440](https://peps.python.org/pep-0440/) for Python package versions.

## [Unreleased]

### Added
- New `CValueExtractor` implementation (`termlint/extraction/extractors/cvalue.py`) with:
  - C-Value scoring over aggregated candidate frequencies
  - dual candidate generation strategy (spaCy mode + heuristic fallback)
  - modular support package: `candidate_generators`, `scorer`, `tokenizer`, `config`, `types`
- Extractor documentation at `termlint/extraction/extractors/README.md`.
- Dedicated C-Value tests:
  - `tests/extraction/extractors/cvalue/test_cvalue_extractor.py`
  - `tests/extraction/extractors/cvalue/test_cvalue_generators.py`
  - `tests/extraction/extractors/cvalue/test_cvalue_scorer.py`

### Changed
- `ParallelStage` async extraction loop now includes an inline typing ignore for `_extract` iteration in `termlint/extraction/stages/parallel.py`.
- User config discovery test updated to validate `%APPDATA%/termlint/config.toml` fallback behavior in `tests/test_config_discovery.py`.
- Added `CValueExtractor` export in `termlint.extraction` module lazy imports.
- Added extraction config section `cvalue` in `termlint/config.py` and enabled `cvalue` initialization in `UnifiedPipeline.from_config()`.
- Default extraction config now enables both `rule` and `cvalue` extractors.
- CValue defaults in `termlint/config.py` and pipeline wiring now reuse constants from `termlint/extraction/extractors/cvalue_support/config.py` as a single source of truth.

## [0.1.0a2] - 2026-03-06

### Added
- `project.urls` metadata (`Homepage`, `Repository`, `Issues`, `Changelog`) for PyPI project links.
- README badges for PyPI version, license, Python versions, and CI workflow status.

### Changed
- README Quick Start updated to installation-independent flow (`input.txt` instead of repository sample paths).
- README sample content switched to English-focused defaults (`en_core_web_sm` in install/config examples).
- README now explicitly documents `pip install --pre "termlint[base]"` for alpha installs.
- Language support section clarified: tested RU/EN models, other spaCy models marked experimental.

## [0.1.0a1] - 2026-03-05

### Summary

First public alpha release of `termlint` CLI with end-to-end terminology linting,
stable CLI contracts, and glossary bootstrap/merge workflows.

### Added
- Global logging configuration with CLI controls: `-v/-q`, `--log-level`, `--log-file`.
- Config path override via `--config` and multi-level config discovery:
  explicit config, nearest project `pyproject.toml`, user config locations, built-in defaults.
- Deterministic progress UI for CLI commands with file-level and stage-level progress bars.
- New glossary tooling:
  - `termlint glossary from-report`
  - `termlint glossary merge`
- New `termlint/glossary` module (`converter`, `merge`, `io`, `models`, `utils`).
- Glossary conversion/merge report artifacts:
  `glossary_generated.json`, `glossary_merged.json`,
  `glossary_merge_conflicts.json`, `glossary_merge_summary.json`.
- Tests for logging level resolution, config discovery, glossary conversion, and glossary merge.

### Changed
- `verify` and `ci` now require explicit `--source` glossary path.
- Rule extractor model auto-download is now opt-in (`auto_download_model`), default disabled.
- Rule extractor install guidance fixed to `termlint[base]`.
- Exit code handling standardized across CLI commands:
  - `0` success
  - `1` quality gate fail
  - `2` usage/config error
  - `3` internal runtime/pipeline error
- Exit codes represented via `ExitCode` `IntEnum`.
- JSON exporter metadata version is now derived from package metadata (no hardcoded version).

### Fixed
- Removed hardcoded test glossary path from default project configuration.
- Replaced traceback-style failures in key CLI flows with clean user-facing error messages.
- Fixed incorrect `click.Abort(3)` usage in `validate`.

### Documentation
- README now includes:
  - complete Quick Start
  - alpha status and supported scope
  - compatibility matrix
  - glossary JSON schema and glossary tooling usage
  - language support policy
  - stable exit code contract
  - config discovery behavior
- ARCHITECTURE updated to include the new glossary layer and generated artifacts.
