"""Verification layer for terminology matching"""
from termlint.verifier.sources.base import KnowledgeSource
from termlint.verifier.sources.json_glossary import JSONGlossarySource

from termlint.verifier.stages.exact import ExactVerificationStage
from termlint.verifier.stages.fuzzy import FuzzyVerificationStage

from termlint.verifier.factory import VerifierFactory


__all__ = [
    "KnowledgeSource",
    "JSONGlossarySource",
    "ExactVerificationStage",
    "FuzzyVerificationStage",
    "VerifierFactory"
]
