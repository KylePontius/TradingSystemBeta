"""
Simulate.py
-----------
Top-level simulation entry point.

Usage:
    from Backtest.Simulation.Simulate import run
    results = run("Configs/example.yaml")
"""

import pandas as pd
import polars as pl
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta

from Core.Config.loader import load
from Core.Config.specs.backtest import BacktestSpec
from Core.Signals.signalEngine import ensure as ensureSignal
from Core.DateProcessing.TradingDays import getTradingDays, getFirstAndLast
from Backtest.Portfolio.MasterPortfolio import MasterPortfolio
from Backtest.Simulation.Rebalance import rebalance


def run(configPath: str | Path) -> MasterPortfolio:
    """
    Run a full backtest from a YAML config file.

    Parameters
    ----------
    configPath : str or Path
        Path to the YAML config file.

    Returns
    -------
    MasterPortfolio
        The master portfolio after the full simulation, containing
        NAV history, trading history, and any remaining active cohorts.
    """

    # 1. Load and validate config
    spec = load(configPath)
    run  = spec.run
    strat = spec.strategy

    # 2. Ensure signal artifact exists (compute if not cached)
    signalPath = ensureSignal(spec.signal)

    # 3. Build formation schedule
    #    Each entry is (formationDate, endDate) — both are first trading
    #    days of their respective calendar months.
    schedule = _buildSchedule(
        start=pd.Timestamp(run.start),
        end=pd.Timestamp(run.end),
        holdingPeriods=strat.holdingPeriods,
        holdingUnit=strat.holdingUnit,
    )

    if not schedule:
        raise ValueError("No formation dates generated — check run.start/end and strategy.")

    # 4. Initialise master portfolio
    master = MasterPortfolio(
        name=run.name,
        startDate=schedule[0][0],
        balance=float(run.capital),
    )

    # 5. Main simulation loop
    for cohortIndex, (formationDate, endDate) in enumerate(schedule):
        # Mark master NAV to market on this formation date
        # (prices as of this date, before any trades)
        master.markToMarket(formationDate)

        # Rebalance: exit expired cohorts, enter new cohort
        master = rebalance(
            master=master,
            formationDate=formationDate,
            endDate=endDate,
            signalPath=signalPath,
            strategy=strat,
            cohortIndex=cohortIndex,
        )

    # 6. Final mark-to-market on last date
    lastFormationDate = schedule[-1][0]

    for portfolio in master.portfolios[:]:
        master.exitPortfolio(lastFormationDate, portfolio)

    return master


# Helpers
def _buildSchedule(
    start:          pd.Timestamp,
    end:            pd.Timestamp,
    holdingPeriods: int,
    holdingUnit:    str,
) -> list[tuple[datetime, datetime]]:
    """
    Build a list of (formationDate, endDate) pairs.

    formationDate — first trading day of each calendar month in [start, end)
    endDate       — first trading day of the month that is holdingPeriods
                    units after formationDate

    Both dates are resolved to actual trading days.
    """

    # Get all trading days in the full range (with buffer for endDate resolution)
    bufferEnd = end + relativedelta(months=holdingPeriods + 2)
    tradingDays = getTradingDays(start, bufferEnd)
    monthTable  = getFirstAndLast(tradingDays)

    # Build a lookup: (year, month) -> first trading day of that month
    firstDayLookup = {
        (int(row["year"]), int(row["month"])): pd.Timestamp(row["first"])
        for row in monthTable.to_dict(orient="records")
    }

    schedule = []
    cursor = pd.Timestamp(start)

    while cursor <= end:
        key = (cursor.year, cursor.month)
        if key not in firstDayLookup:
            cursor += relativedelta(months=1)
            continue

        formationDate = firstDayLookup[key]

        # Compute end month
        endMonth = cursor + relativedelta(**{_unitToKwarg(holdingUnit): holdingPeriods})
        endKey   = (endMonth.year, endMonth.month)

        if endKey not in firstDayLookup:
            # End date falls beyond our trading day data — stop
            break

        endDate = firstDayLookup[endKey]

        schedule.append((formationDate, endDate))
        cursor += relativedelta(months=1)

    return schedule


def _unitToKwarg(unit: str) -> str:
    mapping = {
        "days":   "days",
        "weeks":  "weeks",
        "months": "months",
    }
    if unit not in mapping:
        raise ValueError(f"Unknown holdingUnit: {unit!r}")
    return mapping[unit]

# Phased out, maybe can use for something else?
def _lastTradingDayOnOrBefore(date: pd.Timestamp) -> pd.Timestamp:
    """Find the last trading day on or before the given date."""
    from Core.DateProcessing.TradingDays import getTradingDays
    days = getTradingDays(date - relativedelta(days=10), date)
    valid = [d for d in days if pd.Timestamp(d) <= date]
    if not valid:
        raise ValueError(f"No trading day found on or before {date}")
    return pd.Timestamp(valid[-1])