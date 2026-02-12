from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class TextEntity:
    """
    Unified representation for extracted term
    """
    text: str                # normalized text content
    original_text: str       # original text content before normalization
    lemma: str               # lemma of term
    span: Tuple[int, int]    # start and end positions in the original text
    score: float             # candidate rating

    # context
    pos_tags: List[str] = field(default_factory=list)    # POS tags for the term tokens
    sentence: str = ""                                   # Sentence where the term occurs
    frequency: int = 1                                   # Frequency of the term in the document

    # metadata
    extractor_type: str = ""                                    # Which extractor produced this entity
    properties: Dict[str, Any] = field(default_factory=dict)    # Extra features (tf-idf, embedding, etc.)

    @property
    def normalized_form(self) -> str:
        return self.lemma[0] if hasattr(self, 'lemmas') and self.lemma else self.text.lower()
