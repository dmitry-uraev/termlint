# Samples Commands

This document contains reference commands for different termlint usage scenarios.

## Creating glossary

> **Prerequisites**
>
> - Run commands from repository root.
> - Use the shared config: `samples/generate_ontology.toml`
> - Empty glossary source for ontology bootstrap: `samples/empty_glossary.json`

Example for `ml`:

```bash
mkdir -p samples/reports/ml/glossary

termlint --config samples/generate_ontology.toml verify samples/texts/ml.ru.txt \
    --source samples/empty_glossary.json \
    --output-dir samples/reports/ml/
```

Verify and manually edit terms under `samples/reports/ml/ontology_update.json`. Remove bad candidates, edit terms.

Create glossary from report:

```bash
termlint --config samples/generate_ontology.toml glossary from-report \
    --report samples/reports/ml/ontology_update.json \
    --out samples/reports/ml/glossary/glossary_generated.json \
    --min-score 0.0 --min-frequency 1 --namespace ml
```

Run verification of the same text (`ml.txt`) against the generated glossary:

```bash
termlint --config samples/generate_ontology.toml verify samples/texts/ml.ru.txt \
    --source samples/reports/ml/glossary/glossary_generated.json \
    --output-dir samples/reports/ml/
```
