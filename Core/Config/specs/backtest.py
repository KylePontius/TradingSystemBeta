from dataclasses import dataclass
from .run import RunSpec
from .strategy import StrategySpec
from .signal import SignalSpec


@dataclass(frozen=True)
class BacktestSpec:
    """
    Top-level spec that fully describes a backtest run.

    run:      Name, date range, starting capital.
    strategy: Cohort formation, holding period, capital/position allocation.
    signal:   Factor pipeline that produces buy/sell candidates each period.
    """

    run:      RunSpec
    strategy: StrategySpec
    signal:   SignalSpec