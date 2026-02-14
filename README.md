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
poetry install --with dev --extras "rule ml nlp"
```
