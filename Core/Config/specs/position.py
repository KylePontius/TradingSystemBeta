from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PositionAllocationSpec:
    """
    Specifies how capital within a cohort portfolio is distributed
    across its individual positions.

    method:
        'equal'           - each position receives an equal dollar allocation
        'valueWeighted'   - positions weighted by market cap
        'signalWeighted'  - positions weighted proportionally to their signal score
    """

    method: Literal['equal', 'valueWeighted', 'signalWeighted']

    def identity(self) -> dict:
        return {
            'method': self.method,
        }
