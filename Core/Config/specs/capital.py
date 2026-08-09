from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class CapitalAllocationSpec:
    """
    Specifies how capital is allocated to each new cohort portfolio.

    basis:
        'nav'   - target is computed as a fraction of current master NAV
        'fixed' - target is a fixed dollar amount regardless of NAV

    method:
        'equalSplit' - target = NAV / number of active cohorts
                       (derived from holdingPeriods in StrategySpec)

    shortfallPolicy:
        'investAvailable' - invest min(target, availableCash). Default.
        'skip'            - do not form cohort if cash < target
        'scaleExisting'   - claw back proportionally from live cohorts
                            to fully fund the new one
    """

    basis:           Literal['nav', 'fixed']
    method:          Literal['equalSplit']
    shortfallPolicy: Literal['investAvailable', 'skip', 'scaleExisting'] = 'investAvailable'

    def __post_init__(self):
        if self.basis == 'fixed' and self.method == 'equalSplit':
            raise ValueError(
                "capitalAllocation.method='equalSplit' requires basis='nav'"
            )

    def identity(self) -> dict:
        return {
            'basis':           self.basis,
            'method':          self.method,
            'shortfallPolicy': self.shortfallPolicy,
        }
