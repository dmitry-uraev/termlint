# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows
[PEP 440](https://peps.python.org/pep-0440/) for Python package versions.

## [0.1.0a3] - 2026-03-09

### Added
- New configurable `CValueExtractor` for term extraction.

### Changed
- Added `cvalue` extraction configuration with parameters for threshold, frequency, candidate length, linguistic filtering, spaCy model selection, and model auto-download behavior.
- Default extraction config now enables both `rule` and `cvalue` extractors.

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
