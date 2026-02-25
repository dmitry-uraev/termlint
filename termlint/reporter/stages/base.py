from typing import List, Optional, Union

from termlint.core.models import QualityConfig, Report, ReportConfig
from termlint.core.stages import ProcessingStage
from termlint.core.types import Result, TextEntityStream, MatchResultStream


class ReportStage(ProcessingStage[Union[TextEntityStream, MatchResultStream], List[Report]]):
    """
    Universal ReportStage - handles all report types from any pipeline position.

    Input: TextEntityStream | MatchResultStream
    Output: List[Report] + exported files + quality gates
    """
    def __init__(
            self,
            config: Optional[ReportConfig] = None,
            quality_config: Optional[QualityConfig] = None
    ) -> None:
        self.config = config or ReportConfig()
        self.quality_config = quality_config or QualityConfig()

    async def process(self, stream: Union[TextEntityStream, MatchResultStream]) -> Result[List[Report]]:
        # step 1. match stream type -> generate reports
        # step 2. export using config exporters
        # step 3. quality gates
        ...
