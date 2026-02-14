# termlint Architecture

## Overview

`termlint` is a terminology linter for projects in different subject areas. It extracts term candidates from text, processes them through an asynchronous pipeline, and verifies them against a glossary or knowledge base.

At a high level:

```text
Raw Text
  └─▶ Parallel extraction (Rule / CValue / KeyBERT)
        └─▶ TextEntityStream
              └─▶ Extraction stages (Normalize → Filter → Rank)
                    └─▶ Clean TextEntityStream
                          └─▶ Verifier / Ontology / Report (TODO)
```

## Design Principles

| Principle               | Description                                 |
| ----------------------- | ------------------------------------------- |
| Universal Models        | TextEntity, Entity, Result                  |
| Async Streams           | TextEntityStream[AsyncIterator[TextEntity]] |
| Chain of Responsibility | ExtractionStage pipeline                    |
| Composition             | ParallelStage + sequential stages           |
| Fluent API              | TextExtractionPipeline                      |

## Core Models & Types

| Name             | Purpose                  | Key Fields/Methods                                      |
| ---------------- | ------------------------ | ------------------------------------------------------- |
| TextEntity       | Extracted term candidate | text, original_text, lemma, span, score, extractor_type |
| Entity           | Glossary term            | id, label, synonyms, relations                          |
| Result[T]        | Error handling monad     | ok(value), err(errors), map(), bind()                   |
| TextEntityStream | Async term iterator      | async for, to_list(), from_list()                       |

## Extraction Layer

### Architecture

> Concept

```text
Text ───┐
        ├───> RuleExtractor ────┐
        ├───> CValueExtractor ──┼───▶ ParallelStage
        └───> KeyBERTExtractor ─┘
                                   ▼
                             TextEntityStream (raw candidates)
                                   ▼
                         ExtractionStage pipeline
                     (Normalize → Filter(min_score) → Rank)
                                   ▼
                            TextEntityStream (refined)
```

### Directory Layout

```text
extraction/
├── extractors/        # str → AsyncIterator[TextEntity]
│   ├── base.py        # BaseExtractor + ConfigurableExtractor
│   └── rule.py        # RuleExtractor (spaCy)
├── stages/            # Stream → Result[Stream]
│   ├── parallel.py    # ParallelStage (asyncio.gather)
│   ├── base.py        # ExtractionStage(ABC)
│   └── normalize.py   # NormalizationStage
└── pipeline.py        # TextExtractionPipeline (Fluent API)
```

### Components

| Component              | Location    | Input → Output                              | Contract                                                             |
| ---------------------- | ----------- | ------------------------------------------- | -------------------------------------------------------------------- |
| BaseExtractor          | extractors/ | str → AsyncIterator[TextEntity]             | Abstract                                                             |
| ConfigurableExtractor  | extractors/ | str → AsyncIterator[TextEntity]             | ``**config`` passed to init                                          |
| RuleExtractor          | extractors/ | str → AsyncIterator[TextEntity]             | spaCy patterns, POS tags (Matcher + model autoloading)               |
| ParallelStage          | stages/     | str → Result[TextEntityStream]              | Parallel extractor composition, ``asyncio.gather(*extractor(text))`` |
| ExtractionStage        | stages/     | TextEntityStream → Result[TextEntityStream] | Abstract, Chain of responsibility                                    |
| NormalizationStage     | stages/     | TextEntityStream → Result[TextEntityStream] | Lowercase, lemmatization                                             |
| TextExtractionPipeline | pipeline.py | Fluent config → Result[Stream/List]         | Declarative pipeline builder                                         |

### Extractors

| Extractor        | Algorithm                    | Dependencies          |
| ---------------- | ---------------------------- | --------------------- |
| RuleExtractor    | spaCy patterns, POS-tags     | spacy                 |
| CValueExtractor  | Statistical C-Value/NC-Value | None                  |
| KeyBERTExtractor | Transformer embeddings       | sentence-transformers |

Ideas for keywords extraction:

- https://github.com/MaartenGr/KeyBERT
- https://huggingface.co/ilsilfverskiold/tech-keywords-extractor

### Fluent Pipeline API

> Concept

```python
from termlint.extraction import pipeline

# Declarative pipeline
result = await (pipeline()
    .extractors(rule_extractor, cvalue_extractor)
    .normalize()
    .filter(min_score=0.2)
    .run_and_collect(text))

if result.is_ok:
    terms = result.value  # List[TextEntity]
else:
    errors = result.errors
```

### Result Monad Contract

Every stage returns Result[TextEntityStream]:

```text
ParallelStage.extract(text) → Result[TextEntityStream]
ExtractionStage.process(stream) → Result[TextEntityStream]
TextExtractionPipeline.run(text) → Result[TextEntityStream]
```

Errors propagate automatically:

```python
result = await stage.process(stream)
if not result.is_ok:
    return result  # Pipeline stops here
```

### Error Handling Flow

> Concept

```text
Extractor fails → Result.err(["Extractor 'RuleExtractor': ValueError..."])
                ↓
ParallelStage catches → Result.err([...])
                ↓
Pipeline propagates → Result.err([...])
                ↓
CLI shows errors → Exit code 3
```

## Verifier

> Concept

| Компонент          | Назначение                 | Контракт                                                               |
| ------------------ | -------------------------- | ---------------------------------------------------------------------- |
| KnowledgeSource    | Протокол источников знаний | get_entity(term: str) → Result[Entity]                                 |
| JSONGlossarySource | JSON файл глоссария        | glossary.json → Entity[]                                               |
| SPARQLSource       | Ontology via SPARQL        | SELECT ?term WHERE { ... }                                             |
| TermMatcher        | Поиск совпадений           | match(entity: TextEntity, source: KnowledgeSource) → List[MatchResult] |
| CoverageCalculator | Метрики покрытия           | terms: List[TextEntity], matches: List[MatchResult] → CoverageMetrics  |

## Reporter

| Компонент       | Назначение           | Контракт                                    |
| --------------- | -------------------- | ------------------------------------------- |
| ReportGenerator | Генератор отчётов    | generate(matches: List[MatchResult]) → Dict |
| JSONExporter    | Техническая выгрузка | Dict → JSON                                 |
| HTMLReport      | Человекочитаемый     | Dict → HTML                                 |
| JUnitExporter   | CI/CD                | Dict → JUnit XML                            |
| CoverageMetrics | Статистика           | coverage_pct, unknown_terms, quality_score  |

## Configuration (pyproject.toml)

> Concept

```text
[tool.termlint]
source = "glossary.json"
quality-gate.min-coverage = 0.90
quality-gate.max-unknown = 5

[tool.termlint.extraction]
extractors = ["rules", "cvalue", "keybert"]
pipeline = [
    { stage = "normalize" },
    { stage = "filter", min_score = 0.2 },
    { stage = "rank" }
]

[tool.termlint.sources.platform]
path = "terms/export.json"
term-col = "label"
synonyms-col = "synonyms"
```

## CLI Interface

> Concept

```text
# Verify terminology in project
termlint verify docs/ --source glossary.json --min-coverage 0.95

# Extract terms only
termlint extract text.txt --extractors "rules,cvalue"

# CI/CD quality gates
termlint ci                 # Fail if coverage < 90%

# Generate HTML report
termlint report docs/ --format html --output report.html
```

> Layer concept

| Компонент      | Команда          | Вывод                    |
| -------------- | ---------------- | ------------------------ |
| VerifyCommand  | termlint verify  | Coverage + unknown terms |
| ExtractCommand | termlint extract | Сырые TextEntity[]       |
| ReportCommand  | termlint report  | HTML/JSON экспорт        |
| QualityGate    | termlint ci      | Exit code 0/1            |

## Exit codes

> Concept

```text
0  → PASS (coverage ≥ 90%)
1  → LOW_COVERAGE (< 90%)
2  → TOO_MANY_UNKNOWN (> 5 unknown terms)
3  → CONFIG_ERROR
```

## Ideas

```text
[ ] KnowledgeSource protocols
    ├─ JSONGlossarySource
    ├─ OntologyAPISource (SPARQL)
    └─ PlatformDBSource (CSV/Excel)

[ ] Advanced Verifier
    ├─ Fuzzy matching (rapidfuzz)
    ├─ Semantic matching (embeddings)
    └─ Ontology reasoning (OWLReady2)

[ ] Reports & Visualizations
    ├─ Interactive HTML dashboard
    ├─ JUnit XML for CI
    └─ Coverage heatmaps

[ ] Plugin System
    └─ Custom extractors via entrypoints
```

| Сценарий                | Extraction | Processing | Verification | Ontology | Report |
| ----------------------- | ---------- | ---------- | ------------ | -------- | ------ |
| 1. Полный               | ✅          | ✅          | ✅            |          | ✅      |
| 2. Только извлечение    | ✅          |            |              |          | ✅      |
| 3. Извлечение+обработка | ✅          | ✅          |              |          | ✅      |
| 4. До онтологии         | ✅          | ✅          |              | ✅        | ✅      |
| 5. Из готового          |            |            | ✅            | ✅        | ✅      |
