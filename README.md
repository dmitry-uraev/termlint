# termlint

Terminology linter for projects — extracts terms from code/docs and verifies coverage against your glossary/ontology.

> Concept

```text
Raw Text → Parallel Extractors → Async Pipeline → Glossary Match → Quality Report
  ↓        (rules,cvalue,keybert)   (norm,filter,rank)     ↓
TextEntityStream ────────────────────────→ Coverage 90%
```

Async functional pipeline with composable stages and universal TextEntity model.

## Quick Start

TODO

## Development

```bash
poetry config virtualenvs.in-project true --local
poetry env use python3.12
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
extractors = ["rule"]
rules = { model = "ru_core_news_sm", auto_download_model = false }
```

Set `auto_download_model = true` only if you explicitly want runtime model download (not recommended for CI).

## Exit Codes

`termlint` uses a stable exit code contract:

- `0`: successful run
- `1`: quality gate failed (`ci` command)
- `2`: usage/configuration error (invalid options/config/source)
- `3`: internal pipeline/runtime error
