from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel


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
    pos_tags: List[str] = field(default_factory=list)
    sentence: str = ""
    frequency: int = 1

    # metadata
    extractor_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_form(self) -> str:
        return self.lemma[0] if hasattr(self, 'lemmas') and self.lemma else self.text.lower()
