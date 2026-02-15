"""Base protocol for knowledge sources (glossary/ontology access)"""

from abc import ABC, abstractmethod
from typing import List, Optional

from termlint.core.types import Result
from termlint.core.models import Entity


class KnowledgeSource(ABC):
    """Abstract base class for knowledge sources (glossary/ontology access)"""

    @abstractmethod
    async def get_entity(self, term: str) -> Result[Entity]:
        """Find single term (exact/fuzzy match) and return its entity representation"""
        ...

    @abstractmethod
    async def get_entities(self, terms: List[str]) -> Result[List[Entity]]:
        """Find multiple terms and return their entity representations"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections/resources"""
        ...
