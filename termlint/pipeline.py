"""Unified pipeline for termlint stages"""
from termlint.extraction.stages.normalize import NormalizationStage


class UnifiedPipeline:
    def __init__(self):
        self._stages = []

    def normalize(self):
        self._stages.append(NormalizationStage())
        return self
