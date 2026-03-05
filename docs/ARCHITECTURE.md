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
                                          └─▶ Glossary tools (from-report / merge)
                                                └─▶ glossary_generated.json / glossary_merged.json / conflicts / summary
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
├── glossary/
│   ├── converter.py         # ONTOLOGY_UPDATE candidates -> Entity[]
│   ├── merge.py             # Entity[] merge with policies + conflicts
│   ├── io.py                # Report/Glossary JSON load+save helpers
│   ├── models.py            # MergePolicy, MergeConflict, MergeSummary
│   └── utils.py             # canonical term + deterministic id helpers
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
                          │   (JSONGlossarySource)
                          └─── VerifierFactory ────────┼───▶ Result[MatchResultStream]
                                 │                     │
                                 ├── ExactVerification │
                                 ├── FuzzyVerification │
                                 └── (Semantic/Ensemble)
                                                       ▼
                                              CoverageMetrics + Report
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
├── stages/
│   ├── exact.py            # Exact term matching
│   ├── semantic.py         # word2vec term matching (TODO)
│   ├── ensemble.py         # Any combination term matching (TODO)
│   └── fuzzy.py            # Fuzzy term matching
└── factory.py              # Builds verifier of the specified type according to config
```

### Components (Partly)

| Component          | Location        | Input → Output                        | Contract                                                                 | Status |
| ------------------ | --------------- | ------------------------------------- | ------------------------------------------------------------------------ | ------ |
| KnowledgeSource    | sources/base.py | str → Result[Entity]                  | Abstract knowledge source protocol get_entity(term), get_entities(terms) | +      |
| JSONGlossarySource | sources/        | path → Entity[]                       | Loads glossary.json file → in-memory index                               | +      |
| SPARQLSource       | sources/        | endpoint → Entity[]                   | SPARQL queries → Entity (ontology via SPARQL)                            | TODO   |
| Verifier           | stages/         | TextEntityStream -> MatchResultStream | Extraction → Matching → Results (exact, fuzzy)                           | +      |
| VerifierFactory    | factory.py      | VerifierConfig → ProcessingStage      | Unified entrypoint for verifier creation from type + config parameters   | +      |

```python
class VerifierFactory:
    @staticmethod
    async def create(config: VerifierConfig) -> ProcessingStage:
        # Source creation + validation
        # Unified defaults from config.get_effective_params()
        # Exact | Fuzzy dispatch
```

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
                    └─→ reports/verification.json, reports/ontology_update.json, reports/quality_gate.json
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


## Glossary Layer (Done)

### Architecture (Done)

> Converts `ONTOLOGY_UPDATE` reports into glossary JSON and merges updates with existing glossaries

```text
reports/ontology_update.json
          │
          └───▶ glossary from-report
                    └───▶ glossary_generated.json
                               │
existing glossary.json ────────┼───▶ glossary merge
                               │      (on-match / on-conflict policies)
                               └───▶ glossary_merged.json + merge_conflicts.json + merge_summary.json
```

### Directory Layout (Done)

```text
glossary/
├── __init__.py
├── converter.py      # convert_candidates_to_entities(candidates) -> Entity[]
├── merge.py          # merge_entities(base, updates, policy) -> (merged, conflicts, summary)
├── io.py             # load/write report+glossary JSON
├── models.py         # MatchPolicy, ConflictPolicy, MergePolicy, MergeConflict, MergeSummary
└── utils.py          # canonical_term(), stable_id()
```

### Components (Done)

| Component                             | Location              | Input -> Output                            | Contract                                           | Status         |
| ------------------------------------- | --------------------- | ------------------------------------------ | -------------------------------------------------- | -------------- |
| `convert_candidates_to_entities`      | glossary/converter.py | `List[TextEntity] -> List[Entity]`         | canonical dedupe by lemma/text + deterministic IDs | +              |
| `merge_entities`                      | glossary/merge.py     | `base + updates -> merged/conflicts`       | policy-based merge (`skip                          | merge-synonyms | replace`) + conflicts | + |
| `load_suggested_entities_from_report` | glossary/io.py        | ontology_update JSON -> `List[TextEntity]` | validates `data.suggested_entities` shape          | +              |
| `load_entities_from_glossary`         | glossary/io.py        | glossary JSON -> `List[Entity]`            | validates glossary entity shape                    | +              |
| `write_entities_to_glossary`          | glossary/io.py        | `List[Entity] -> glossary.json`            | deterministic JSON serialization                   | +              |

### Generated Reports / Artifacts (Done)

| Artifact                                | Produced By                                   | Type                 | Description                                                                                    |
| --------------------------------------- | --------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------- |
| `reports/glossary_generated.json`       | `termlint glossary from-report`               | Glossary JSON        | Generated glossary entities from `reports/ontology_update.json` (deduplicated, stable IDs).    |
| `reports/glossary_merged.json`          | `termlint glossary merge`                     | Glossary JSON        | Final merged glossary from `--base` + `--updates` according to selected merge policy.          |
| `reports/glossary_merge_conflicts.json` | `termlint glossary merge --conflicts-out ...` | Conflict report JSON | List of merge conflicts (`id_label_mismatch`, `ambiguous_term_match`, etc.) for manual review. |
| `reports/glossary_merge_summary.json`   | `termlint glossary merge --summary-out ...`   | Summary report JSON  | Merge counters: `added`, `updated`, `skipped`, `conflicts` to support CI/automation.           |

Notes:
- `--conflicts-out` and `--summary-out` are optional; if omitted, only merged glossary is produced.
- Same schema applies for conflict demo files (e.g., `glossary_merge_conflict_details.json`, `glossary_merge_conflict_summary.json`).


## Configuration (pyproject.toml) (Partly)

> Concept of DSL for configuring term extraction flows

```text
[tool.termlint]
output_dir = "reports/"

[tool.termlint.extraction]
extractors = ["rule"]
rules.model = "ru_core_news_sm"

[tool.termlint.verifier]
source = "domain_terms.json"
type = "fuzzy"                    # exact | fuzzy
fuzzy = {                         # config.get_fuzzy_defaults()
    threshold = 85,               # 85%+ = NEAR_MATCH
    limit = 3,                    # top-N candidates
    scorer = "token_sort_ratio"
}

[tool.termlint.reports]
include = ["verification", "quality_gate"]
exporters = ["json"]

[tool.termlint.pipeline]
stages = ["extract", "normalize", "verify", "report"]
```

### Config Layer Flow (Partly)

> Concept: Priority: CLI args -> pyproject.toml -> defaults

TODO: refactor other layers

Implemented for verification layer:

```text
pyproject.toml
  ↓ Pydantic (TermlintConfig)
config.get_fuzzy_defaults()    # Centralized defaults
  ↓
VerifierFactory.create()       # Validation + Creation
  ↓
ProcessingStage (no defaults)  # Clean stages
```

UnifiedPipeline.from_config() example for verify stage:

```python
case "verify":
    verifier = await VerifierFactory.create(config.verifier)
    pipeline.verify(verifier)
```

## CLI Interface (Done)

```text
# Full pipeline (default)
termlint verify README.md --source glossary.json --verifier fuzzy --threshold 85

# Extract terms only
termlint extract docs/

# CI/CD quality gates
termlint ci README.md --source glossary.json

# Glossary bootstrap from ontology update report
termlint glossary from-report --report reports/ontology_update.json --out glossary.generated.json
termlint glossary merge --base glossary.json --updates glossary.generated.json --out glossary.merged.json

# Config
termlint config
termlint validate
```

> Layer concept

| Command              | Scenario | Output                                       | Exit codes |
| -------------------- | -------- | -------------------------------------------- | ---------- |
| verify               | 1, 4     | Reports + files                              | 0, 2, 3    |
| extract              | 2, 3     | EXTRACTION report                            | 0, 2, 3    |
| ci                   | 5        | QUALITY_GATE only                            | 0, 1, 2, 3 |
| glossary from-report | 4        | `glossary_generated.json`                    | 0, 2, 3    |
| glossary merge       | 4, 5     | merged glossary + optional conflicts/summary | 0, 2, 3    |
| config               | -        | Effective config (JSON)                      | 0, 2       |
| validate             | -        | Config validation                            | 0, 2       |

### Exit codes (Done)

Stable CLI contract:

```text
0  -> PASS / successful execution
1  -> QUALITY_GATE_FAIL (ci command)
2  -> USAGE_OR_CONFIG_ERROR (invalid options/config/source/input files)
3  -> INTERNAL_PIPELINE_ERROR (unexpected runtime errors)
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
