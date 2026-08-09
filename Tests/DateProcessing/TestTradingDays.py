import pytest
import pandas as pd
import polars as pl
import numpy as np
from datetime import datetime
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from Core.DateProcessing.TradingDays import *

# Load real MSFT data
BASE = "C:/Users/Kyle/.vscode/projects/TradingSystem/StockData"
TICKER = "MSFT"
folder = f"{BASE}/ticker={TICKER}"

# Load only the date column for performance
dates = (
    pl.scan_parquet(folder)
    .select("date")
    .collect()
    .to_numpy()
)

# Invalid type tests

@pytest.mark.parametrize(
    "date,endDate",
    [
        ("invalid", datetime(2025, 1, 1)),           # non-convertible start
        (datetime(2025, 1, 1), {"a": 1}),    # non-convertible end
    ]
)
def test_getTradingDays_invalid_types(date, endDate):
    with pytest.raises(TypeError):
        getTradingDays(date, endDate)


@pytest.mark.parametrize(
    "tradingDays",
    [
        ("invalid"),
        ("2025-01-01"),  # not iterable
    ]
)
def test_getFirstAndLast_invalid_types(tradingDays):
    with pytest.raises(TypeError):
        getFirstAndLast(tradingDays)


@pytest.mark.parametrize(
    "date,tradingDays",
    [
        ("invalid", np.array([datetime(2025, 1, 1)])),
        (datetime(2025, 1, 1), "invalid"),
    ]
)
def test_getLatestTradingDay_invalid_types(date, tradingDays):
    with pytest.raises(TypeError):
        getLatestTradingDay(date, tradingDays)


@pytest.mark.parametrize(
    "date,tradingDays",
    [
        ("invalid", pd.DatetimeIndex([pd.Timestamp("2025-01-01")])),
        (datetime(2025, 1, 1), "invalid"),
    ]
)
def test_getNextTradingDay_invalid_types(date, tradingDays):
    with pytest.raises(TypeError):
        getNextTradingDay(date, tradingDays)


# Functional tests

@pytest.mark.parametrize(
    "startDate,endDate",
    [
        (datetime(2025, 3, 1), datetime(2025, 3, 31)),
    ]
)
def test_getTradingDays_success(startDate, endDate):
    dates = (
        pl.scan_parquet(folder)
        .filter((pl.col("date") >= pl.lit(startDate)) & (pl.col("date") <= pl.lit(endDate)))
        .select("date")
        .collect()
        .to_numpy()
        .flatten()
    )
    np.testing.assert_array_equal(getTradingDays(startDate, endDate), dates)



@pytest.mark.parametrize(
    "startDate,endDate",
    [
        (datetime(2025, 3, 1), datetime(2025, 3, 31)),
    ]
)
def test_getFirstAndLast_success(startDate, endDate):
    tradingDays = getTradingDays(startDate, endDate)
    result = getFirstAndLast(tradingDays)

    filtered = (
        pl.scan_parquet(folder)
        .filter((pl.col("date") >= pl.lit(startDate)) & (pl.col("date") <= pl.lit(endDate)))
        .select("date")
        .collect()
        .to_numpy()
        .flatten()
    )

    filtered = pd.to_datetime(filtered)
    df = pd.DataFrame({"date": filtered})
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    expected = (
        df.groupby(["year", "month"])["date"]
        .agg(["first", "last"])
        .reset_index(drop=True)
    )
    expected["first"] = expected["first"].astype("datetime64[ns]")
    expected["last"]  = expected["last"].astype("datetime64[ns]")

    pd.testing.assert_frame_equal(result[["first", "last"]], expected, check_names=False)

@pytest.mark.parametrize(
    "date",
    [
        datetime(2025, 3, 1),
        datetime(2025, 3, 14),
    ]
)
def test_getLatestTradingDay_success(date):
    tradingDays = getTradingDays(datetime(2025, 2, 1), datetime(2025, 4, 1))
    latestResult = getLatestTradingDay(date, tradingDays)
    latestExpected = dates[dates <= date][-1]
    assert latestResult == latestExpected


@pytest.mark.parametrize(
    "date",
    [
        datetime(2025, 3, 1),
        datetime(2025, 3, 14),
    ]
)
def test_getNextTradingDay_success(date):
    tradingDays = getTradingDays(datetime(1997, 12, 31), datetime(2025, 4, 1))
    nextResult = getNextTradingDay(date, tradingDays)
    nextExpected = dates[dates > date][0]
    assert nextResult == nextExpected


#pytest -vv Tests\DateProcessing\TestTradingDays.py