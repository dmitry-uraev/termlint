# termlint Architecture

## Overview (Partly)

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

## Design Principles (Done)

| Principle               | Description                                 |
| ----------------------- | ------------------------------------------- |
| Universal Models        | TextEntity, Entity, Result                  |
| Async Streams           | TextEntityStream[AsyncIterator[TextEntity]] |
| Chain of Responsibility | ExtractionStage pipeline                    |
| Composition             | ParallelStage + sequential stages           |
| Fluent API              | TextExtractionPipeline                      |

## Core Models & Types (Partly)

| Name              | Purpose                                              | Key Fields/Methods                                      | Location       | Status |
| ----------------- | ---------------------------------------------------- | ------------------------------------------------------- | -------------- | ------ |
| TextEntity        | Extracted term candidate                             | text, original_text, lemma, span, score, extractor_type | core/models.py | Partly |
| Entity            | Glossary term                                        | id, label, synonyms, relations, definition              | core/models.py | TODO   |
| MatchResult       | Extraction -> Glossary link (TextEntity -> Entity)   | text_entity, entity, confidence, status                 | core/models.py | TODO   |
| Result[T]         | Error handling monad                                 | ok(value), err(errors), map(), bind()                   | core/types.py  | +      |
| TextEntityStream  | Async term iterator (provides extraction results)    | async for entity in stream, to_list(), from_list()      | core/types.py  | +      |
| MatchResultStream | Async match iterator (provides verification results) | async for match in stream, to_list(), from_list()       | core/types.py  | TODO   |
| CoverageReport    | Final metrics + details                              | coverage_pct, unknown_terms, matches                    | core/types.py  | TODO   |

## Common Layers Principles

### Result Monad Contract (TODO)

Every stage returns Result[TextEntityStream]:

```text
ExtractionStage.process(TextEntityStream)      →    Result[TextEntityStream]
VerificationStage.process(TextEntityStream)    →    Result[MatchResultStream]
ReportStage.process(MatchResultStream)         →    Result[CoverageReport]

pipeline.run(text) → Result[FinalOutput]    # type depends on the last stages
```

Errors propagate automatically:

```python
result = await stage.process(stream)
if not result.is_ok:
    return result  # Pipeline stops here
```

### Fluent Pipeline API (TODO)

> Concept: Unified Processing Graph (extends extraction layer)

```python
from termlint import pipeline

# Extended pipeline: Extraction → Verification → Report
result = await (pipeline()
    .extractors(rule_extractor, cvalue_extractor)
    .normalize()
    .filter(min_score=0.2)
    .verify(glossary="glossary.json")      # verification layer stages
    .report()                              # reporter layer stage
    .run_and_collect(text))

if result.is_ok:
    report = result.value  # CoverageMetrics + MatchResult[]
```

### Stage Implementation Strategy (TODO)

core/stages.py

Abstract pipeline stage

```python
# core/stages.py
class ProcessingStage(ABC, Generic[TInput, TOutput]):
    async def process(self, input: TInput) -> Result[TOutput]: ...
```

extraction/stages/normalization.py

```python
class NormalizationStage(ProcessingStage[TextEntityStream, TextEntityStream]): ...
```

### Directory Layout (TODO)

> TODO: Unify

```text
termlint/
├── core/
│   ├── types.py             # Entity, MatchResult
│   └── stages.py            # ProcessingStage[Input, Output]
├── extraction/
│   └── stages/              # ExtractionStage → ProcessingStage
├── verifier/
│   └── stages/              # VerificationStage → ProcessingStage
├── reporter/
│   └── stages/              # ReportStage → ProcessingStage
└── pipeline.py              # UnifiedPipeline
```

### Error Handling Flow (Partly)

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

## Extraction Layer (Partly)

### Architecture (Done)

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

### Directory Layout (Done)

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

### Components (Partly)

| Component              | Location    | Input → Output                              | Contract                                                             | Status |
| ---------------------- | ----------- | ------------------------------------------- | -------------------------------------------------------------------- | ------ |
| BaseExtractor          | extractors/ | str → AsyncIterator[TextEntity]             | Abstract                                                             | +      |
| ConfigurableExtractor  | extractors/ | str → AsyncIterator[TextEntity]             | ``**config`` passed to init                                          | +      |
| RuleExtractor          | extractors/ | str → AsyncIterator[TextEntity]             | spaCy patterns, POS tags (Matcher + model autoloading)               | +      |
| CValueExtractor        | extractors/ | str → AsyncIterator[TextEntity]             | TODO                                                                 | TODO   |
| KeyBERTExtractor       | extractors/ | str → AsyncIterator[TextEntity]             | TODO                                                                 | TODO   |
| ParallelStage          | stages/     | str → Result[TextEntityStream]              | Parallel extractor composition, ``asyncio.gather(*extractor(text))`` | +      |
| ExtractionStage        | stages/     | TextEntityStream → Result[TextEntityStream] | Abstract, Chain of responsibility                                    | +      |
| NormalizationStage     | stages/     | TextEntityStream → Result[TextEntityStream] | Lowercase, lemmatization                                             | +      |
| FilterStage            | stages/     | TextEntityStream → Result[TextEntityStream] | TODO                                                                 | TODO   |
| RankStage              | stages/     | TextEntityStream → Result[TextEntityStream] | TODO                                                                 | TODO   |
| TextExtractionPipeline | pipeline.py | Fluent config → Result[Stream/List]         | Declarative pipeline builder                                         | Partly |

### Extractors (Partly)

| Extractor        | Algorithm                    | Dependencies          | Status |
| ---------------- | ---------------------------- | --------------------- | ------ |
| RuleExtractor    | spaCy patterns, POS-tags     | spacy                 | +      |
| CValueExtractor  | Statistical C-Value/NC-Value | None                  | TODO   |
| KeyBERTExtractor | Transformer embeddings       | sentence-transformers | TODO   |

Ideas for keywords extraction:

- https://github.com/MaartenGr/KeyBERT
- https://huggingface.co/ilsilfverskiold/tech-keywords-extractor

## Verification Layer (TODO)

### Architecture (TODO)

> Concept

```text
Clean TextEntityStream ───┐
                          ├─── KnowledgeSource ───┐
                          │   (JSONGlossary, SPARQL)  │
                          └─── TermMatcher ───────┼───▶ List[MatchResult]
                                                      │
                                                      ▼
                                               CoverageMetrics + Report
```

Input: TextEntityStream (from Extraction Layer)
Output: List[MatchResult] + CoverageMetrics

### Directory Layer (TODO)

```text
verifier/
├── __init__.py
├── sources/                # KnowledgeSource implementations (Ontology)
│   ├── __init__.py
│   ├── base.py             # KnowledgeSource(Protocol)
│   ├── json_glossary.py    # JSONGlossarySource
│   └── sparql.py           # SPARQLSource (TODO)
├── matcher.py              # TermMatcher (comparison logic)
└── verifier.py             # BasicVerifier (orchestration)
```

### Components (TODO)

> Concept

| Component          | Location        | Input → Output                       | Contract                                                                                        | Status |
| ------------------ | --------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------- | ------ |
| KnowledgeSource    | sources/base.py | str → Result[Entity]                 | Abstract knowledge source protocol get_entity(term), get_entities(terms)                        | TODO   |
| JSONGlossarySource | sources/        | path → Entity[]                      | Loads glossary.json file → in-memory index                                                      | TODO   |
| SPARQLSource       | sources/        | endpoint → Entity[]                  | SPARQL queries → Entity (ontology via SPARQL)                                                   | TODO   |
| TermMatcher        | matcher.py      | TextEntityStream → List[MatchResult] | Exact/fuzzy/semantic term matching algorithm match(entity: TextEntity, source: KnowledgeSource) | TODO   |
| BasicVerifier      | verifier.py     | str + pipeline → List[MatchResult]   | Extraction → Matching → Results                                                                 | TODO   |
| CoverageCalculator | REPORTER LAYER? | REPORTER LAYER?                      | Coverage metrics terms: List[TextEntity], matches: List[MatchResult] → CoverageMetrics          | TODO   |

## Reporter (TODO)

| Компонент       | Назначение           | Контракт                                    |
| --------------- | -------------------- | ------------------------------------------- |
| ReportGenerator | Генератор отчётов    | generate(matches: List[MatchResult]) → Dict |
| JSONExporter    | Техническая выгрузка | Dict → JSON                                 |
| HTMLReport      | Человекочитаемый     | Dict → HTML                                 |
| JUnitExporter   | CI/CD                | Dict → JUnit XML                            |
| CoverageMetrics | Статистика           | coverage_pct, unknown_terms, quality_score  |

## Configuration (pyproject.toml) (TODO)

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

## CLI Interface (TODO)

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

### Exit codes (TODO)

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

## Usage scenarios (Partly)

| Сценарий                | Extraction | Processing | Verification | Ontology | Report | Описание                                                                   |
| ----------------------- | ---------- | ---------- | ------------ | -------- | ------ | -------------------------------------------------------------------------- |
| 1. Полный               | +          | +          | +            |          | +      | Извлечение, обработка, верификация по существующей онтологии и отчет.      |
| 2. Только извлечение    | +          |            |              |          | +      | Извлечение и отчет.                                                        |
| 3. Извлечение+обработка | +          | +          |              |          | +      | Извлечение, обработка и отчет.                                             |
| 4. До онтологии         | +          | +          |              | +        | +      | Извлечение, обработка, построение онтологии по извлеченным данным и отчет. |
| 5. Из готового          |            |            | +            | +        | +      | ?                                                                          |
