"""
MarketCap.py
------------
Point-in-time market cap lookup from Sharadar SF1 fundamentals.

Uses the most recent quarterly report (ARQ) filed on or before the
trade date to avoid lookahead bias.

The full SF1 table is loaded once and cached in memory for performance.
"""

import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from Core.Config.paths import SHARADAR_DIR


@lru_cache(maxsize=1)
def _loadSF1() -> pl.DataFrame:
    """
    Load and cache the SF1 fundamentals table.
    Filters to quarterly dimension (ARQ) and keeps only
    ticker, datekey, and marketcap.
    """
    path = SHARADAR_DIR / "sharadarSF1.csv"
    if not path.exists():
        raise FileNotFoundError(f"SF1 data not found at {path}")

    return (
        pl.read_csv(path, try_parse_dates=True)
        .filter(pl.col("dimension") == "ARQ")
        .select(["ticker", "datekey", "marketcap"])
        .filter(pl.col("marketcap").is_not_null())
        .sort(["ticker", "datekey"])
    )


def getMarketCap(date: datetime, ticker: str) -> float | None:
    """
    Get the most recent point-in-time market cap for a ticker on a given date.

    Uses the latest ARQ filing with datekey <= trade date.
    Returns None if no data is available.

    Parameters
    ----------
    date : datetime or pd.Timestamp
        The trade date.
    ticker : str
        The stock ticker.

    Returns
    -------
    float or None
        Market cap in dollars, or None if unavailable.
    """
    date = pd.Timestamp(date).date()

    sf1 = _loadSF1()

    result = (
        sf1
        .filter(
            (pl.col("ticker") == ticker) &
            (pl.col("datekey") <= pl.lit(date))
        )
        .sort("datekey")
        .tail(1)
        .select("marketcap")
    )

    if result.is_empty():
        return None

    return float(result.item())