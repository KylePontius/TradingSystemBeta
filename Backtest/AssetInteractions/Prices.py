from datetime import datetime
import numpy as np
import polars as pl
import pandas as pd
from pathlib import Path
from functools import lru_cache

from Core.Config.paths import STOCK_DIR

BASE = STOCK_DIR


@lru_cache(maxsize=1000)
def loadTicker(ticker: str) -> pl.LazyFrame:
    return pl.scan_parquet(f"{BASE}/ticker={ticker}/0.parquet")


def getOpen(date: datetime, ticker: str) -> np.float64:
    """Grab open price for ticker on a given date"""
    if not isinstance(date, (datetime, pd.Timestamp)):
        raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")
    if not isinstance(ticker, str):
        raise TypeError(f"Expected str for ticker, got {type(ticker)}")

    folder = BASE / f"ticker={ticker}"
    if not folder.exists():
        raise FileNotFoundError(f"No data for {ticker}")

    df = (
    loadTicker(ticker)
    .filter(pl.col("date") == pl.lit(pd.Timestamp(date).date()))
    .select("open")
    .collect(engine="streaming")
    )

    if df.is_empty():
        raise ValueError(f"No data exists for {date} in {ticker}")

    return np.float64(df.item())


def getClose(date: datetime, ticker: str) -> np.float64:
    """Grab close price for ticker on a given date"""
    if not isinstance(date, (datetime, pd.Timestamp)):
        raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")
    if not isinstance(ticker, str):
        raise TypeError(f"Expected str for ticker, got {type(ticker)}")

    folder = BASE / f"ticker={ticker}"
    if not folder.exists():
        raise FileNotFoundError(f"No data for {ticker}")

    df = (
    loadTicker(ticker)
    .filter(pl.col("date") == pl.lit(pd.Timestamp(date).date()))
    .select("close")
    .collect(engine="streaming")
    )

    if df.is_empty():
        raise ValueError(f"No data exists for {date} in {ticker}")

    return np.float64(df.item())


def getAdjustedClose(date: datetime, ticker: str) -> np.float64:
    """Grab adjusted close price for ticker on a given date"""
    if not isinstance(date, (datetime, pd.Timestamp)):
        raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")
    if not isinstance(ticker, str):
        raise TypeError(f"Expected str for ticker, got {type(ticker)}")

    folder = BASE / f"ticker={ticker}"
    if not folder.exists():
        raise FileNotFoundError(f"No data for {ticker}")

    df = (
    loadTicker(ticker)
    .filter(pl.col("date") == pl.lit(pd.Timestamp(date).date()))
    .select("closeadj")
    .collect(engine="streaming")
    )

    if df.is_empty():
        raise ValueError(f"No data exists for {date} in {ticker}")

    return np.float64(df.item())