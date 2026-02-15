from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, auto


# Extraction Layer -----------------------------------------

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
        return self.lemma.lower()


# Verification Layer -----------------------------------------

@dataclass(frozen=True)
class Entity:
    id:            str                                                   # unique identifier ("glossary:001", "ontology:1234", etc.)
    label:         str                                                   # "term", "concept", "entity", etc.
    synonyms:      List[str] = field(default_factory=list)               # list of synonymous names/labels for this entity
    relations:     Dict[str, List[str]] = field(default_factory=dict)    # relation type -> list of related entity ids
    definition:    Optional[str] = None                                  # textual definition or description of the entity
    source:        Optional[str] = None                                  # source of the entity (glossary name, ontology IRI, etc.)


class MatchStatus(Enum):

    MATCHED = auto()
    UNKNOWN = auto()
    AMBIGUOUS = auto()
    NEAR_MATCH = auto()


@dataclass(frozen=True)
class MatchResult:
    text_entity: TextEntity
    entity: Optional[Entity] = None
    confidence: float = 0.0
    status: MatchStatus = MatchStatus.UNKNOWN
    matched_synonym: Optional[str] = None
