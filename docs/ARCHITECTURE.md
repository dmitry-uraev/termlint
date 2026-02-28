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
                          └─▶ Verification stage (Exact, Fuzzy, Semantic, Ensemble) + OntologySource
                                └─▶ MatchResultStream
                                    └─▶  Report stage (Ontology coverage and statistics reporting and exporting)
```

## Design Principles (Done)

| Principle               | Description                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| Universal Models        | TextEntity, Entity, Result, MatchResult, Report                                            |
| Async Streams           | TextEntityStream[AsyncIterator[TextEntity]], MatchResultStream[AsyncIterator[MatchResult]] |
| Chain of Responsibility | ExtractionStage pipeline (extractors combination)                                          |
| Composition             | ParallelStage + sequential stages (extracted data processing)                              |
| Fluent API              | TextExtractionPipeline (all in one place, different processing combinations)               |
| Universal Reporting     | Single ReportStage handles all report types via config                                     |

## Core Models & Types (Done)

| Name              | Purpose                                              | Key Fields/Methods                                      | Location       | Status |
| ----------------- | ---------------------------------------------------- | ------------------------------------------------------- | -------------- | ------ |
| TextEntity        | Extracted term candidate                             | text, original_text, lemma, span, score, extractor_type | core/models.py | +      |
| Entity            | Glossary term                                        | id, label, synonyms, relations, definition              | core/models.py | +      |
| MatchResult       | Extraction -> Glossary link (TextEntity -> Entity)   | text_entity, entity, confidence, status                 | core/models.py | +      |
| Report            | Polymorphic final metrics (all report types)         | report_type, coverage_pct, unknown_terms, matches       | core/models.py | +      |
| ReportType        | Report types enum                                    | EXTRACTION\|VERIFICATION\|ONTOLOGY_UPDATE etc.          | core/models.py | +      |
| ReportConfig      | ReportStage configuration                            | include, exporters, quality_gates                       | core/models.py | +      |
| QualityConfig     | CI/CD quality gates                                  | check(reports) -> bool                                  | core/models.py | +      |
| Result[T]         | Error handling monad                                 | ok(value), err(errors), map(), bind()                   | core/types.py  | +      |
| TextEntityStream  | Async term iterator (provides extraction results)    | async for entity in stream, to_list(), from_list()      | core/types.py  | +      |
| MatchResultStream | Async match iterator (provides verification results) | async for match in stream, to_list(), from_list()       | core/types.py  | +      |

## Common Layers Principles (Partly)

### Result Monad Contract (Done)

Every stage returns Result[TextEntityStream]:

```text
ExtractionStage.process(TextEntityStream)                       →    Result[TextEntityStream]
VerificationStage.process(TextEntityStream)                     →    Result[MatchResultStream]
ReportStage.process(TextEntityStream|MatchResultStream)         →    Result[List[Report]]

pipeline.run(text) → Result[FinalOutput]    # Report[] + exported files
```

Errors propagate automatically:

```python
result = await stage.process(stream)
if not result.is_ok:
    return result  # Pipeline stops here
```

### Fluent Pipeline API (Done)

> Concept: Unified Processing Graph (extends extraction layer)

```python
from termlint import pipeline

# Base pipeline scenario: Extraction -> Processing -> Verification -> Report
result = await (pipeline()
    .extractors(rule_extractor, cvalue_extractor)    # extraction stage
    .normalize()                                     # processing stage
    .filter(min_score=0.2)                           # processing stage
    .verify(fuzzy_stage)                             # verification layer stage
    .report(include=[VERIFICATION, QUALITY_GATE])    # reporter layer stage
    .run_and_collect(text))                          # pass text

if result.is_ok:
    report = result.value  # List[Report] + files created
```

### Stage Implementation Strategy (Partly)

core/stages.py

Abstract pipeline stage

```python
class ProcessingStage(ABC, Generic[TInput, TOutput]):
    async def process(self, input: TInput) -> Result[TOutput]: ...
```

extraction/stages/base.py

```python
class ExtractionStage(ProcessingStage[TextEntityStream, TextEntityStream], ABC): ...
```

extraction/stages/normalization.py

```python
class NormalizationStage(ExtractionStage): ...
```

verifier/stages/exact.py

```python
class ExactVerificationStage(ProcessingStage[TextEntityStream, MatchResultStream]):
```

verifier/stages/fuzzy.py

```python
class FuzzyVerificationStage(ProcessingStage[TextEntityStream, MatchResultStream]):
```

### Directory Layout (Done)

```text
termlint/
├── core/
│   ├── types.py             # Result, TextEntityStream, MatchResultStream
│   ├── stages.py            # ProcessingStage[Input, Output]
│   └── models.py            # TextEntity, Entity, MatchResult, MatchStatus, Report, ReportType, ReportConfig, QualityConfig
├── extraction/
│   ├── stages/              # ParallelStage, NormalizationStage (and others) -> ExtractionStage (base extraction stage) -> ProcessingStage
│   └── extractors/          # Base Extractor + Rule Based (+ KeyBERT, CValue)
├── verifier/
│   ├── stages/              # ExactVerificationStage, FuzzyVerificationStage
│   └── sources/             # KnowledgeSource, JSONGlossarySource
├── reporter/
│   └── stages/              # ReportStage → ProcessingStage
└── pipeline.py              # UnifiedPipeline
```

### Error Handling Flow (Done)

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
| TextExtractionPipeline | pipeline.py | Fluent config → Result[Stream/List]         | Declarative pipeline builder                                         | +      |

### Extractors (Partly)

| Extractor        | Algorithm                    | Dependencies          | Status |
| ---------------- | ---------------------------- | --------------------- | ------ |
| RuleExtractor    | spaCy patterns, POS-tags     | spacy                 | +      |
| CValueExtractor  | Statistical C-Value/NC-Value | None                  | TODO   |
| KeyBERTExtractor | Transformer embeddings       | sentence-transformers | TODO   |

Ideas for keywords extraction:

- https://github.com/MaartenGr/KeyBERT
- https://huggingface.co/ilsilfverskiold/tech-keywords-extractor

## Verification Layer (Partly)

### Architecture (Done)

> Concept

```text
Clean TextEntityStream ───┐
                          ├─── KnowledgeSource ───┐
                          │   (JSONGlossary, SPARQL)
                          └─── VerificationStage ───────┼───▶ Result[MatchResultStream]
                                                        │
                                                        ▼
                                                 CoverageMetrics + Report (Reporting Layer)
```

Input: TextEntityStream (from Extraction Layer)
Output: Result[MatchResultStream]

### Directory Layer (Done)

```text
verifier/
├── __init__.py
├── sources/                # KnowledgeSource implementations (Ontology)
│   ├── __init__.py
│   ├── base.py             # KnowledgeSource(Protocol)
│   ├── json_glossary.py    # JSONGlossarySource
│   └── sparql.py           # SPARQLSource (TODO)
└── stages/
    ├── exact.py            # Exact term matching
    ├── semantic.py         # word2vec term matching (TODO)
    ├── ensemble.py         # Any combination term matching (TODO)
    └── fuzzy.py            # Fuzzy term matching
```

### Components (Partly)

| Component          | Location        | Input → Output                        | Contract                                                                 | Status |
| ------------------ | --------------- | ------------------------------------- | ------------------------------------------------------------------------ | ------ |
| KnowledgeSource    | sources/base.py | str → Result[Entity]                  | Abstract knowledge source protocol get_entity(term), get_entities(terms) | +      |
| JSONGlossarySource | sources/        | path → Entity[]                       | Loads glossary.json file → in-memory index                               | +      |
| SPARQLSource       | sources/        | endpoint → Entity[]                   | SPARQL queries → Entity (ontology via SPARQL)                            | TODO   |
| Verifier           | stages/         | TextEntityStream -> MatchResultStream | Extraction → Matching → Results (exact, fuzzy)                           | +      |

## Reporter (Partly)

### Architecture (Done)

> Universal ReportStage processes any stream → multiple Report types + exports

```text
TextEntityStream ───┐
MatchResultStream ──┼───▶ ReportStage ───┐
                    │                    ├─── Report[] (VERIFICATION, ONTOLOGY_UPDATE...)
                    │                    ├─── Parallel Export (JSON, HTML, JUnit)
                    │                    └─── Quality Gates → Result[ok/err]
                    │
                    └─→ reports/verification.json, suggestions.json, coverage.html
```

Input: TextEntityStream | MatchResultStream
Output: Result[List[Report]] + generated files

### Directory Layout (Done)

```text
reporter/
├── __init__.py
├── stages/
│   └── base.py          # ReportStage(ProcessingStage[Union[Stream], List[Report]])
├── exporters/           # JSONExporter, HTMLExporter, JUnitExporter
│   ├── __init__.py
│   ├── json.py
│   ├── html.py
│   └── junit.py
├── generators.py        # ReportType logic (VERIFICATION → ONTOLOGY_UPDATE from same data)
└── config.py            # ReportConfig, QualityConfig (imported from core)
```

### Components (Partly)

| Component     | Location           | Input -> Output                        | Contract                                                             | Status |
| ------------- | ------------------ | -------------------------------------- | -------------------------------------------------------------------- | ------ |
| ReportStage   | stages/base.py     | Union[Streams] -> List[Report] + files | Universal: aggregation, export, quality gates                        | +      |
| Report        | core/models.py     | Polymorphic metrics                    | report_type (EXTRACTION\|VERIFICATION \| ...) suggested_entities     | +      |
| JSONExporter  | exporters/json.py  | Report -> JSON file                    | Universal serialization (adapts to report type)                      | +      |
| HTMLExporter  | exporters/html.py  | Report -> HTML dashboard               | Jinja2 templates per report_type (coverage chart, suggestions table) | TODO   |
| JUnitExporter | exporters/junit.py | Report -> JUnit XML                    | Only QUALITY_GATE\|VERIFICATION data for CI                          | TODO   |
| ReportConfig  | core/models.py     | Fluent params -> ReportStage           | include=[ReportType], exporters=[], quality_gates={}, output_dir     | +      |
| QualityConfig | core/models.py     | Fluent params -> ReportStage           | min_coverage, max_unknown, max_quality_score                         | +      |

### Report types to usage scenarios (Partly)

> TODO: Need parameters clarification, hard-coded constants removing, and usage description

| ReportType      | Input Stream      | Key Metrics                             | Usage Scenario |
| --------------- | ----------------- | --------------------------------------- | -------------- |
| EXTRACTION      | TextEntityStream  | total, avg_score, extractor_stats       | 2, 3           |
| PROCESSING      | TextEntityStream  | total, avg_score, extractor_stats       | 2, 3           |
| VERIFICATION    | MatchResultStream | coverage_pct, unknown_terms             | 1              |
| ONTOLOGY_UPDATE | MatchResultStream | suggested_entities (high_score unknown) | 4              |
| QUALITY_GATE    | Any               | pass/fail, exit_code                    | CI/CD          |


## Configuration (pyproject.toml) (TODO)

> Concept of DSL for configuring term extraction flows

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

> TODO: implement CLI tool for all usage scenarios

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

| Component      | Command          | Output                   |
| -------------- | ---------------- | ------------------------ |
| VerifyCommand  | termlint verify  | Coverage + unknown terms |
| ExtractCommand | termlint extract | Сырые TextEntity[]       |
| ReportCommand  | termlint report  | HTML/JSON экспорт        |
| QualityGate    | termlint ci      | Exit code 0/1            |

### Exit codes (TODO)

> Concept, these should be configurable as well

```text
0  → PASS (coverage ≥ 90%)
1  → LOW_COVERAGE (< 90%)
2  → TOO_MANY_UNKNOWN (> 5 unknown terms)
3  → CONFIG_ERROR
```

## Ideas

```text
[x] KnowledgeSource protocols
    ├─ [x] JSONGlossarySource
    ├─ OntologyAPISource (SPARQL)
    └─ PlatformDBSource (CSV/Excel)

[x] Advanced Verifier
    ├─ [x] Fuzzy matching (rapidfuzz)
    ├─ Semantic matching (embeddings)
    └─ Ontology reasoning (OWLReady2)

[x] Reports & Visualizations
    ├─ [x] Reports to files (JSONExporter)
    ├─ Interactive HTML dashboard
    ├─ JUnit XML for CI
    └─ Coverage heatmaps

[ ] Plugin System
    └─ Custom extractors via entrypoints
```

## Usage scenarios (Partly)

| Scenario                   | Extraction | Processing | Verification | Report Types                  | Usage                                                                                                  |
| -------------------------- | ---------- | ---------- | ------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------ |
| 1. Full                    | +          | +          | +            | VERIFICATION, QUALITY_GATE    | Extract, process, verify against ontology source, and build report (full pipeline + coverage metrics). |
| 2. Just extraction         | +          | -          | -            | EXTRACTION                    | Extract and build report (candidate terms statistics, no verification against existing ontology).      |
| 3. Extraction + processing | +          | +          | -            | PROCESSING                    | Extract, process, and build report (processed candidates statistics, no ontology comparison).          |
| 4. Ontology update         | +          | +          | +            | VERIFICATION, ONTOLOGY_UPDATE | Extract, process, verify against ontology source, and build suggestions report.                        |
| 5. From existing ontology  | -          | -          | +            | VERIFICATION, QUALITY_GATE    | Build report on top of existing ontology.                                                              |

Ontology update reports should be possible to create at each scenario: 1, 2, 3, and 4 except 5.
