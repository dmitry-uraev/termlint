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
