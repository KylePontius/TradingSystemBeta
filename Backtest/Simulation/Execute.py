"""
Execute.py
----------
Translates a signal DataFrame (tickers + signal direction) into a list of
(ticker, weight, direction, slippage) tuples that Portfolio.enterPositions() expects.

Handles position weighting according to PositionAllocationSpec.
"""

import polars as pl
from Core.Config.specs.position import PositionAllocationSpec
from Core.Config.specs.slippage import SlippageSpec


def buildPositions(
    signals:  pl.DataFrame,
    spec:     PositionAllocationSpec,
    slippage: SlippageSpec,
) -> list[tuple[str, float, str, SlippageSpec]]:
    """
    Convert a signal DataFrame into a positions list for enterPositions().

    Parameters
    ----------
    signals : pl.DataFrame
        Must contain columns: ticker, signal, score.
        signal values: 1 = long, -1 = short.
    spec : PositionAllocationSpec
    slippage : SlippageSpec

    Returns
    -------
    list of (ticker, weight, direction, slippage)
    """

    if signals.is_empty():
        return []

    positions = []

    if spec.method == "equal":
        for row in signals.iter_rows(named=True):
            direction = "long" if row["signal"] == 1 else "short"
            positions.append((row["ticker"], 1.0, direction, slippage))

    elif spec.method == "signalWeighted":
        total = signals["score"].abs().sum()
        if total == 0:
            return buildPositions(signals, PositionAllocationSpec(method="equal"), slippage)

        for row in signals.iter_rows(named=True):
            direction = "long" if row["signal"] == 1 else "short"
            weight = abs(row["score"]) / total
            positions.append((row["ticker"], float(weight), direction, slippage))

    elif spec.method == "valueWeighted":
        if "marketcap" not in signals.columns:
            raise ValueError(
                "positionAllocation.method='valueWeighted' requires a "
                "'marketcap' column in the signals DataFrame"
            )
        total = signals["marketcap"].sum()
        for row in signals.iter_rows(named=True):
            direction = "long" if row["signal"] == 1 else "short"
            weight = row["marketcap"] / total
            positions.append((row["ticker"], float(weight), direction, slippage))

    else:
        raise ValueError(f"Unknown positionAllocation.method: {spec.method!r}")

    return positions