# termlint Architecture

## Overview

``termlint`` is a terminology linter for projects in different subject areas.


## Design Principles

Universal Models: ``TextEntity``, ``Entity``, ``Result``.

Async Streams: ``TextEntityStream[AsyncIterator[TextEntity]]``.

Chain of Responsibility: ``ExtractionStage``.

Composition: ``ParallelStage`` + ``ExtractionStage``.

Protocols ``ParallelStage``.

## Core

### Data Models

``TextEntity`` (extracted from text):

```python
@dataclass
class TextEntity:
    text: str                    # Normalized term
    original_text: str           # Original span
    lemma: str                   # Lemmatized form
    score: float                 # Extraction confidence (0.0-1.0)
    pos_tags: List[str]          # ["NOUN", "ADJ"]
    properties: Dict[str, Any]   # tfidf, embeddings, frequency
```

``Entity`` (from knowledge source):

```python
@dataclass
class Entity:
    id: str                      # Ontology IRI / DB PK
    label: str                   # Canonical term
    properties: Dict[str, Any]   # definition, keywords, attributes
    synonyms: List[str]          # Alternative forms
    relations: Dict[str, List]   # {"parent": ["entity_id"]}
```

Core Types

```python
Result[T]           # Error-handling monad (Rust-inspired)
TextEntityStream    # AsyncIterator[TextEntity] wrapper
```

``Result`` Monad:

```python
Result.ok("term").map(str.lower).bind(async_validate) → Result[str]
Result.err(["invalid"]).map(str.lower) → Result.err(["invalid"])
```

## Extraction Layer

### High-Level Flow

#### Concept

```text
Text ───┐
        ├───> RuleExtractor ───┐
        ├───> CValueExtractor ─┼───> ParallelStage ───┐
        └───> KeyBERTExtractor ─┘                      │
                                                    ▼
                                             Extraction Pipeline
                                       ┌──────────────┼──────────────┐
                                       │              │              │
                                 Normalize       Filter(min_score)  Rank
                                       │              │              │
                                       └──────────────┼──────────────┘
                                                    │
                                               TextEntityStream
```

#### ``ExtractionStage`` (Chain of Responsibility)

```text
graph LR
    A[Raw Stream] --> B[NormalizeStage]
    B --> C[FilterStage]
    C --> D[RankStage]
    D --> E[Result Stream]

    B -.->|next_stage| C
    C -.->|next_stage| D
```

#### Base Implementation

```python
class ExtractionStage(ABC):
    async def process(self, stream: TextEntityStream) -> TextEntityStream:
        transformed = await self._handle(stream)
        return await self._next.process(transformed) if self._next else transformed

    @abstractmethod
    async def _handle(self, stream: TextEntityStream) -> TextEntityStream:
        pass
```

#### ``ParallelStage`` (Extractor Composition)

```python
class ParallelStage:
    def __init__(self, extractors: List[Callable[[str], AsyncIterator[TextEntity]]]):
        self.extractors = extractors

    async def extract(self, text: str) -> TextEntityStream:
        # Runs all extractors in parallel, merges results
        pass
```

#### ``Extractors``

| Extractor        | Algorithm                      | Dependencies          |
| ---------------- | ------------------------------ | --------------------- |
| RuleExtractor    | spaCy patterns, POS-tags       | spacy                 |
| CValueExtractor  | Statistical (C-Value/NC-Value) | None                  |
| KeyBERTExtractor | Transformer embeddings         | sentence-transformers |

#### Fluent Pipeline API

> Concept

```python
pipeline = (TextExtractionPipeline()
    .parallel([rules, cvalue, keybert])
    .normalize()
    .filter(min_score=0.2, min_length=2)
    .rank()
    .run(text))
```

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
