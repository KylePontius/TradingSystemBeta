from dataclasses import dataclass
from typing import Literal
from .capital import CapitalAllocationSpec
from .position import PositionAllocationSpec
from .slippage import SlippageSpec

@dataclass(frozen=True)
class StrategySpec:
    """
    Specifies the simulation strategy — how cohorts are formed, held,
    and how capital is allocated within and across them.

    formationFrequency:
        How often a new cohort portfolio is formed.
        'monthly' | 'weekly' | 'daily'

    timeBasis:
        Whether formation dates are resolved using calendar time
        or trading days.
        'calendar' | 'trading'

    holdingPeriods:
        How long each cohort lives before being exited.
        Must be a positive integer.

    holdingUnit:
        The unit for holdingPeriods.
        'days' | 'weeks' | 'months'

    capitalAllocation:
        How much capital to deploy into each new cohort.
        See CapitalAllocationSpec.

    positionAllocation:
        How capital within a cohort is split across positions.
        See PositionAllocationSpec.

    Notes
    -----
    The number of simultaneously active cohorts is derived automatically:
        maxCohorts = holdingPeriods  (when formationFrequency matches holdingUnit)
    For example: form monthly, hold 6 months → 6 active cohorts at any time.
    """

    formationFrequency: Literal['daily', 'weekly', 'monthly']
    timeBasis:          Literal['calendar', 'trading']
    holdingPeriods:     int
    holdingUnit:        Literal['days', 'weeks', 'months']
    capitalAllocation:  CapitalAllocationSpec
    positionAllocation: PositionAllocationSpec
    slippage: SlippageSpec = SlippageSpec()  # defaults to size-based spread

    def __post_init__(self):
        if self.holdingPeriods <= 0:
            raise ValueError("StrategySpec.holdingPeriods must be positive")

    def identity(self) -> dict:
        return {
            'formationFrequency': self.formationFrequency,
            'timeBasis':          self.timeBasis,
            'holdingPeriods':     self.holdingPeriods,
            'holdingUnit':        self.holdingUnit,
            'capitalAllocation':  self.capitalAllocation.identity(),
            'positionAllocation': self.positionAllocation.identity(),
        }