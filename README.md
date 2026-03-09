# termlint

[![PyPI version](https://img.shields.io/pypi/v/termlint)](https://pypi.org/project/termlint/)
![License](https://img.shields.io/pypi/l/termlint)
![Python versions](https://img.shields.io/pypi/pyversions/termlint)
[![CI](https://github.com/dmitry-uraev/termlint/actions/workflows/termlint_ci.yaml/badge.svg)](https://github.com/dmitry-uraev/termlint/actions/workflows/termlint_ci.yaml)

Terminology linter for projects — extracts terms from code/docs and verifies coverage against your glossary/ontology.

## What Is termlint?

`termlint` is a CLI tool for terminology quality checks in text/documentation workflows.

- extracts term candidates from text
- verifies terms against your glossary (`exact`/`fuzzy`)
- generates JSON reports (`verification`, `ontology_update`, `quality_gate`, `extraction`)
- helps bootstrap and evolve glossaries (`glossary from-report`, `glossary merge`)

> Concept

```text
Raw Text → Parallel Extractors → Async Pipeline → Glossary Match → Quality Report
  ↓        (rules,cvalue,keybert)   (norm,filter,rank)     ↓
TextEntityStream ────────────────────────→ Coverage 90%
```

Async functional pipeline with composable stages and universal TextEntity model.

## Alpha Status

`termlint` is currently **alpha**.

Implemented and supported now:
- rule-based extraction (`RuleExtractor` / spaCy)
- C-Value extraction module (`CValueExtractor`) with spaCy mode and heuristic fallback
- verification: `exact`, `fuzzy`
- report export: JSON (`extraction`, `verification`, `ontology_update`, `quality_gate`)
- glossary tooling: `glossary from-report`, `glossary merge`

Planned / not implemented yet:
- extractor integration in config/CLI: `KeyBERT`
- processing stages: `filter`, `rank`
- verification stages: `semantic`, `ensemble`
- exporters: HTML, JUnit

### Latest Branch Changes (Unreleased)

- Added `CValueExtractor` implementation under `termlint/extraction/extractors/`:
  - modular candidate generation (`spaCy` + heuristic fallback)
  - standalone C-Value scorer module
  - tokenizer/config/type support modules
- Added dedicated C-Value test suite:
  - extractor behavior tests
  - candidate generator tests
  - scorer math tests
- Updated extraction stage internals to silence typing noise for async extractor iteration.

## Compatibility Matrix

| Dimension                | Current support                                                            |
| ------------------------ | -------------------------------------------------------------------------- |
| OS                       | Linux, macOS, Windows (CLI, JSON workflows)                                |
| Python (core)            | `>=3.10`                                                                   |
| Python (rule extraction) | `>=3.10,<3.14` with `termlint[base]` (spaCy extra)                         |
| Required extras          | `termlint[base]`                                                           |
| Core deps from extras    | `spacy`, `rapidfuzz`                                                       |
| Default spaCy model      | `ru_core_news_sm`                                                          |
| Console/output language  | English-only CLI and report metadata                                       |
| Tested text languages    | Russian (`ru_core_news_sm`), English (`en_core_web_sm`)                    |
| Other languages          | Possible via `rules.model`, but not yet validated in the alpha test matrix |

### Language Support Policy

- `termlint` pipeline is language-agnostic in design, but extraction quality depends on the selected spaCy model.
- Core CLI/report/glossary functionality supports Python `>=3.10`.
- Rule extraction (`RuleExtractor`) depends on spaCy and is currently supported for Python `<3.14`.
- Officially tested in alpha:
  - Russian with `ru_core_news_sm`
  - English with `en_core_web_sm`
- Other spaCy language models can be used via `[tool.termlint.extraction.rules].model`, but should be treated as experimental until formally tested.
- CLI messages and generated report metadata are in English.

## Quick Start

1. Install:

```bash
# Recommended for CLI usage (isolated global tool)
pipx install "termlint[base]"

# Alternative: project/venv install
pip install --pre "termlint[base]"

# Install spaCy model into the same environment
python -m spacy download en_core_web_sm
```

For `pipx`, install model inside the pipx environment:

```bash
pipx runpip termlint install en-core-web-sm
# or for Russian
pipx runpip termlint install ru-core-news-sm
```

2. Create a minimal glossary (`glossary.json`):

```json
[
  { "id": "ml:001", "label": "machine learning", "synonyms": ["ML"] },
  { "id": "ml:002", "label": "artificial intelligence", "synonyms": ["AI"] }
]
```

3. Create an input text file (`input.txt`):

```text
Artificial intelligence and machine learning are used in data analytics.
```

4. Run verification:

```bash
termlint verify input.txt --source glossary.json --verifier fuzzy --threshold 85
```

5. Expected output (example):

```text
Files     ... 100%
✅ input.txt ... 100%
📊 Coverage: 33.3% (2/6)
⚠️  Quality Gate would FAIL in CI mode
```

Generated reports:
- `reports/verification.json`
- `reports/ontology_update.json`
- `reports/quality_gate.json`

Exit behavior:
- `verify` exits `0` on successful run by default (even if quality gate would fail in CI mode)
- `verify --fail-on-quality-gate` exits `1` when quality gates fail
- full contract is listed in [Exit Codes](#exit-codes)

## Glossary JSON Schema

`termlint` expects a glossary file as a JSON array of objects.

Required fields per entity:
- `id` (`string`)
- `label` (`string`)

Optional fields:
- `synonyms` (`string[]`, default `[]`)
- `relations` (`object<string, string[]>`, default `{}`)
- `definition` (`string | null`)
- `source` (`string | null`)

Minimal valid example:

```json
[
  {
    "id": "ml:001",
    "label": "machine learning"
  }
]
```

Extended example:

```json
[
  {
    "id": "ml:001",
    "label": "machine learning",
    "synonyms": ["ML"],
    "relations": {
      "related_to": ["ml:002"]
    },
    "definition": "Field focused on learning patterns from data.",
    "source": "internal-glossary"
  }
]
```

Common validation/runtime errors:
- File not found: `Glossary file not found: <path>`
- Invalid JSON syntax: `Invalid JSON in <path>: ...`
- Invalid entity shape/type: `Failed to initialize glossary source '<path>': ...`

## Glossary Tooling

Create glossary from `ontology_update` report:

```bash
termlint glossary from-report \
  --report reports/ontology_update.json \
  --out glossary.generated.json \
  --min-score 0.7 \
  --min-frequency 1 \
  --namespace auto
```

Merge generated glossary into an existing glossary:

```bash
termlint glossary merge \
  --base glossary.json \
  --updates glossary.generated.json \
  --out glossary.merged.json \
  --on-match merge-synonyms \
  --on-conflict report \
  --conflicts-out merge.conflicts.json \
  --summary-out merge.summary.json
```

## Development

```bash
poetry config virtualenvs.in-project true --local
poetry env use python3.13
poetry install --with dev --extras "base"
```

## Logging

`termlint` follows common linter-style verbosity controls:

```bash
termlint -v verify <file>        # INFO logs
termlint -vv verify <file>       # DEBUG logs
termlint -q verify <file>        # ERROR only
termlint --log-level DEBUG verify <file>
termlint --log-file reports/termlint.log verify <file>
termlint --config ./pyproject.toml verify <file> --source ./glossary.json
```

You can also set defaults in `pyproject.toml`:

```toml
[tool.termlint.logging]
level = "WARNING"
log_file = "reports/termlint.log"
fmt = "%(asctime)s [%(name)s] %(levelname)-8s %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
max_bytes = 10485760
backup_count = 5
```

spaCy model download is disabled by default during lint runs. Configure extraction like:

```toml
[tool.termlint.extraction]
extractors = ["rule", "cvalue"]
rules = { model = "en_core_web_sm", auto_download_model = false }
cvalue = { threshold = 0.25, min_freq = 1, min_length = 2, max_length = 4, use_ling_filter = true, model = "en_core_web_sm", auto_model_download = false }
```

Set `auto_download_model = true` for rules and `auto_model_download = true` for cvalue only if you explicitly want runtime model download (not recommended for CI).

## Config Discovery

Config lookup order:

1. `--config <PATH>`
2. nearest `pyproject.toml` (searching upward from current directory), section `[tool.termlint]`
3. user-level config:
   - `$XDG_CONFIG_HOME/termlint/config.toml` (if set)
   - `~/.config/termlint/config.toml`
   - `%APPDATA%/termlint/config.toml` (Windows)
   - `~/.termlint/config.toml`
4. built-in defaults

User-level config may use either:
- `[tool.termlint]` (same as project config)
- `[termlint]` (short form for standalone user config files)

## Exit Codes

`termlint` uses a stable exit code contract:

- `0`: successful run
- `1`: quality gate failed (`verify --fail-on-quality-gate`)
- `2`: usage/configuration error (invalid options/config/source)
- `3`: internal pipeline/runtime error
