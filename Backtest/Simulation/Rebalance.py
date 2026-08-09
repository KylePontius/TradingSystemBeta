"""
Rebalance.py
------------
On each formation date:
    1. Exit any cohorts that have reached their holding period end date
    2. Compute capital target for the new cohort
    3. Read signals for this formation date
    4. Build positions list
    5. Add new cohort to MasterPortfolio
"""

import pandas as pd
import polars as pl
from pathlib import Path
from datetime import datetime

from Backtest.Portfolio.MasterPortfolio import MasterPortfolio
from Core.Config.specs.strategy import StrategySpec
from Backtest.Simulation.Accounting import computeCohortTarget
from Backtest.Simulation.Execute import buildPositions


def rebalance(
    master:        MasterPortfolio,
    formationDate: datetime,
    endDate:       datetime,
    signalPath:    Path,
    strategy:      StrategySpec,
    cohortIndex:   int,
) -> MasterPortfolio:
    """
    Perform a single rebalance step on a formation date.

    Parameters
    ----------
    master : MasterPortfolio
    formationDate : datetime
    endDate : datetime
    signalPath : Path
    strategy : StrategySpec
    cohortIndex : int

    Returns
    -------
    MasterPortfolio
    """

    formationDate = pd.Timestamp(formationDate)
    endDate       = pd.Timestamp(endDate)

    # 1. Exit expired cohorts
    expired = [p for p in master.portfolios if p.isExpired(formationDate)]
    for portfolio in expired:
        master.exitPortfolio(formationDate, portfolio)

    # 2. Compute capital target for new cohort
    nav           = master.value(formationDate)
    availableCash = master.balance
    activeCohorts = len(master.portfolios)

    capital = computeCohortTarget(
        nav=nav,
        availableCash=availableCash,
        activeCohorts=activeCohorts,
        holdingPeriods=strategy.holdingPeriods,
        spec=strategy.capitalAllocation,
    )

    if capital <= 0:
        return master

    # 3. Load signals for this formation date
    signals = _loadSignalsForDate(signalPath, formationDate)

    if signals.is_empty():
        return master

    # 4. Build positions list
    positions = buildPositions(
        signals=signals,
        spec=strategy.positionAllocation,
        slippage=strategy.slippage,
    )

    if not positions:
        return master

    # 5. Add new cohort to master portfolio
    cohortName = f"cohort_{cohortIndex:04d}_{formationDate.date()}"

    master.addPortfolio(
        name=cohortName,
        date=formationDate,
        positions=positions,
        allocation=capital,
        endDate=endDate,
        allocationType="absolute",
    )

    return master


def _loadSignalsForDate(signalPath: Path, date: pd.Timestamp) -> pl.DataFrame:
    try:
        df = (
            pl.scan_parquet(signalPath)
            .filter(pl.col("date") == date)
            .collect()
        )
        return df
    except Exception:
        return pl.DataFrame()