# termlint

[![PyPI version](https://img.shields.io/pypi/v/termlint)](https://pypi.org/project/termlint/)
![License](https://img.shields.io/pypi/l/termlint)
![Python versions](https://img.shields.io/pypi/pyversions/termlint)
[![CI](https://github.com/dmitry-uraev/termlint/actions/workflows/termlint_ci.yaml/badge.svg)](https://github.com/dmitry-uraev/termlint/actions/workflows/termlint_ci.yaml)

Terminology linter for projects. `termlint` extracts term candidates from text and checks them against your glossary or ontology.

## Alpha Status

`termlint` is currently **alpha**.

Implemented now:
- rule-based extraction (`RuleExtractor` / spaCy)
- C-Value extraction (`CValueExtractor`)
- verification: `exact`, `fuzzy`
- JSON reports: `verification`, `ontology_update`, `quality_gate`, `extraction`
- glossary tooling: `glossary from-report`, `glossary merge`

Current support is intentionally narrow:
- Python `>=3.10`
- spaCy-based extraction is currently supported on Python `<3.14`
- officially tested with English and Russian spaCy models
- other spaCy models may work, but should be treated as experimental in this alpha stage

## Quick Start

1. Install:

```bash
# Recommended for CLI usage
pipx install "termlint[base]"

# Alternative: install into a project environment
pip install --pre "termlint[base]"

# Install a spaCy model into the same environment
python -m spacy download en_core_web_sm
```

For `pipx`, install the model inside the pipx environment:

```bash
pipx runpip termlint install en-core-web-sm
# or for Russian
pipx runpip termlint install ru-core-news-sm
```

2. Create a glossary (`glossary.json`):

```json
[
  { "id": "ml:001", "label": "machine learning", "synonyms": ["ML"] },
  { "id": "ml:002", "label": "artificial intelligence", "synonyms": ["AI"] }
]
```

3. Create an input file (`input.txt`):

```text
Artificial intelligence and machine learning are used in data analytics.
```

4. Run verification:

```bash
termlint verify input.txt --source glossary.json --verifier fuzzy --threshold 85
```

Example output:

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
- `verify` exits `0` on a successful run by default, even if the quality gate would fail in CI mode
- `verify --fail-on-quality-gate` exits `1` when quality gates fail

## Configuration

Project configuration lives in `pyproject.toml` under `[tool.termlint]`.

Example:

```toml
[tool.termlint.logging]
level = "WARNING"
log_file = "reports/termlint.log"

[tool.termlint.extraction]
extractors = ["rule", "cvalue"]
rules = { model = "en_core_web_sm", auto_download_model = false }
cvalue = { threshold = 0.25, min_freq = 1, min_length = 2, max_length = 4, use_ling_filter = true, model = "en_core_web_sm", auto_download_model = false }
```

Notes:
- use `termlint -v` or `termlint -vv` for more verbose logs
- keep `auto_download_model = false` in CI or reproducible environments
- glossary sources are JSON arrays of entities with required fields `id` and `label`

Minimal valid glossary:

```json
[
  {
    "id": "ml:001",
    "label": "machine learning"
  }
]
```

Config lookup order:

1. `--config <PATH>`
2. nearest `pyproject.toml` with `[tool.termlint]`
3. user config:
   - `$XDG_CONFIG_HOME/termlint/config.toml`
   - `~/.config/termlint/config.toml`
   - `%APPDATA%/termlint/config.toml`
   - `~/.termlint/config.toml`
4. built-in defaults

User config files may use either `[tool.termlint]` or `[termlint]`.

## More Docs

- Usage examples: [samples/USAGE.md](samples/USAGE.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
