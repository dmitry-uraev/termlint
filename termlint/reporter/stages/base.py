from typing import List, Union

from termlint.core.models import Report, ReportConfig
from termlint.core.stages import ProcessingStage
from termlint.core.types import Result, TextEntityStream, MatchResultStream


class ReportStage(ProcessingStage[Union[TextEntityStream, MatchResultStream], List[Report]]):
    def __init__(self, config: ReportConfig) -> None:
        self.config = config or ReportConfig()

    async def process(self, stream: Union[TextEntityStream, MatchResultStream]) -> Result[List[Report]]:
        # step 1. match stream type -> generate reports
        # step 2. export using config exporters
        # step 3. quality gates
        ...
