import pytest
from datetime import datetime
import numpy as np
import sys, os

# Add project root to path so BacktestSystem imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from Backtest.AssetInteractions.Prices import getOpen, getClose, getAdjustedClose


# TYPE CHECK FAILURES

@pytest.mark.parametrize(
    "date,ticker",
    [
        (0, "MSFT"),                     # invalid date
        (datetime(2024, 1, 1), 0),       # invalid ticker
    ]
)
def test_getOpen_fail_invalid_types(date, ticker):
    with pytest.raises(TypeError):
        getOpen(date, ticker)


@pytest.mark.parametrize(
    "date,ticker",
    [
        (0, "MSFT"),
        (datetime(2024, 1, 1), 0),
    ]
)
def test_getClose_fail_invalid_types(date, ticker):
    with pytest.raises(TypeError):
        getClose(date, ticker)

@pytest.mark.parametrize(
    "date,ticker",
    [
        (0, "MSFT"),
        (datetime(2024, 1, 1), 0),
    ]
)
def test_getAdjustedClose_fail_invalid_types(date, ticker):
    with pytest.raises(TypeError):
        getAdjustedClose(date, ticker)



# VALUE ERROR (NO DATA FOUND) 

@pytest.mark.parametrize(
    "date,ticker",
    [
        (datetime(1995, 1, 1), "MSFT"),  # way before data begins
    ]
)
def test_getOpen_fail_date(date, ticker):
    with pytest.raises(ValueError):
        getOpen(date, ticker)


@pytest.mark.parametrize(
    "date,ticker",
    [
        (datetime(1995, 1, 1), "MSFT"),
    ]
)
def test_getClose_fail_date(date, ticker):
    with pytest.raises(ValueError):
        getClose(date, ticker)

@pytest.mark.parametrize(
    "date,ticker",
    [
        (datetime(1995, 1, 1), "MSFT"),
    ]
)
def test_getAdjustedClose_fail_date(date, ticker):
    with pytest.raises(ValueError):
        getAdjustedClose(date, ticker)


# SUCCESS CASES 

@pytest.mark.parametrize(
    "date,ticker,expected",
    [
        (datetime(1997, 12, 31), "MSFT", 16.375),
        (datetime(2025, 5, 30), "MSFT", 459.715),
    ]
)
def test_getOpen_success(date, ticker, expected):
    assert np.isclose(getOpen(date, ticker), expected, atol=1e-6)


@pytest.mark.parametrize(
    "date,ticker,expected",
    [
        (datetime(1997, 12, 31), "MSFT", 16.156),
        (datetime(2025, 5, 30), "MSFT", 460.360),
    ]
)
def test_getClose_success(date, ticker, expected):
    assert np.isclose(getClose(date, ticker), expected, atol=1e-6)

@pytest.mark.parametrize(
    "date,ticker,expected",
    [
        (datetime(1997, 12, 31), "MSFT", 9.925),
        (datetime(2025, 5, 30), "MSFT", 460.360),
    ]
)
def test_getAdjustedClose_success(date, ticker, expected):
    assert np.isclose(getAdjustedClose(date, ticker), expected, atol=1e-6)
     
#pytest Tests/AssetInteractions/TestPrices.py -v
