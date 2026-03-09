# Extractors

This directory contains term extraction stages used by termlint.

## CValueExtractor

`CValueExtractor` ranks multi-word term candidates with the C-Value algorithm.

### Purpose

The extractor is designed for terminology extraction from plain text. It works best on repeated noun-phrase-like expressions such as:

- `machine learning`
- `deep learning`
- `artificial intelligence`
- `нейронные сети`
- `машинное обучение`

### Architecture

The implementation is intentionally split into small components:

- `cvalue.py`
  - extractor orchestration
  - model loading
  - C-Value scoring
  - output conversion to `TextEntity`

- `cvalue_support/tokenizer.py`
  - spaCy tokenization
  - regex fallback tokenization

- `cvalue_support/candidate_generators.py`
  - spaCy-based candidate generation
  - heuristic fallback candidate generation

- `cvalue_support/config.py`
  - default parameters
  - stop words
  - POS rules
  - heuristic rule constants

### Extraction modes

#### 1. spaCy mode

This is the preferred mode.

It uses POS information and sentence boundaries to generate noun-phrase-like candidates with the rule:

`ADJ* + (NOUN|PROPN)+`

Examples:

- `deep learning`
- `large datasets`
- `искусственный интеллект`

If spaCy is enabled and the model is available, this mode is selected automatically.

#### 2. Heuristic mode

This is the fallback mode.

It uses short conservative n-grams inside sentence boundaries and filters them with simple rules:

- reject candidates containing stop words
- reject suspicious capitalization patterns
- reject some common English verb-like endings
- keep candidate length short

This mode is less accurate, but it keeps the extractor usable when no spaCy model is available.

### Fallback behavior

The extractor prefers spaCy mode by default.

If spaCy is not installed or the configured model cannot be loaded:

- heuristic mode is used automatically
- optional model auto-download can be enabled with `auto_download_model=True`

### C-Value scoring

For a candidate `a`:

- if `a` is not nested inside longer candidates:

  `CValue(a) = log2(|a|) * f(a)`

- if `a` is nested:

  `CValue(a) = log2(|a|) * (f(a) - average_parent_frequency(a))`

Where:

- `|a|` is candidate length in tokens
- `f(a)` is candidate frequency
- parent terms are longer candidates containing `a` as a contiguous span

### Notes

- C-Value works best on multi-word terms, so the default minimum length is `2`.
- On very small texts, nested shorter terms often receive score `0.0`. This is expected behavior.
- For mixed-language corpora, select the spaCy model that matches the input language.
