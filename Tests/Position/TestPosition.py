import pytest
import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from Backtest.Position.Position import Position
from Backtest.AssetInteractions.Prices import getOpen, getAdjustedClose
from datetime import datetime


# Type validation
@pytest.mark.parametrize(
    "date,ticker,weight,allocation,direction",
    [
        (0,                      "MSFT", 0.5,  1000, "long"),
        (datetime(2025, 1, 2),   123,    0.5,  1000, "long"),
        (datetime(2025, 1, 2),   "MSFT", "",   1000, "long"),
        (datetime(2025, 1, 2),   "MSFT", 0.5,  "",   "long"),
        (datetime(2025, 1, 2),   "MSFT", 0.5,  1000, 0),
    ]
)
def test_position_invalid_types(date, ticker, weight, allocation, direction):
    with pytest.raises(TypeError):
        Position(date, ticker, weight, allocation, direction)


# Value validation
@pytest.mark.parametrize(
    'date,ticker,weight,allocation,direction',
    [
        (datetime(1990, 1, 1),  "MSFT", 0.5,  1000,  "long"),   # no price data
        (datetime(2025, 5, 30), "MSFT", -0.5, 1000,  "long"),   # negative weight
        (datetime(2025, 5, 30), "MSFT", 0.5,  -1000, "long"),   # negative allocation
        (datetime(2025, 5, 30), "MSFT", 0.5,  -1000, "hold"),   # invalid direction
    ]
)
def test_position_invalid_values(date, ticker, weight, allocation, direction):
    with pytest.raises((ValueError, FileNotFoundError)):
        Position(date, ticker, weight, allocation, direction)


# Helpers
def _expected(date, ticker, weight, allocation, direction, markDate=None, closeDate=None):
    """
    Build a dict of expected Position field values derived from real prices.
    This makes tests price-agnostic — they test the math, not the data.
    """
    entryPrice  = getOpen(date, ticker)
    closePrice0 = getAdjustedClose(date, ticker)

    numShares = (allocation * weight) / entryPrice
    if direction == 'short':
        numShares = -numShares

    entryValue   = round(numShares * entryPrice, 3)
    markedValue0 = round(numShares * closePrice0, 3)
    unrealPnl0   = round(markedValue0 - entryValue, 3)
    unrealPct0   = round(100 * unrealPnl0 / abs(entryValue), 3) if entryValue != 0 else 0.0

    result = {
        'ticker':               ticker,
        'entryDate':            date,
        'direction':            direction.lower(),
        'entryPrice':           entryPrice,
        'weight':               weight,
        'numShares':            numShares,
        'entryValue':           entryValue,
        'markedValue':          markedValue0,
        'unrealizedPnl':        unrealPnl0,
        'unrealizedPnlPercent': unrealPct0,
    }

    if markDate is not None:
        markPrice  = getAdjustedClose(markDate, ticker)
        markValue  = round(numShares * markPrice, 3)
        markUnreal = round(markValue - entryValue, 3)
        markPct    = round(100 * markUnreal / abs(entryValue), 3) if entryValue != 0 else 0.0
        result.update({
            'markDate':            markDate,
            'markPrice':           markPrice,
            'markValue':           markValue,
            'markUnrealizedPnl':   markUnreal,
            'markUnrealizedPct':   markPct,
        })

    if closeDate is not None:
        exitPrice = getOpen(closeDate, ticker)
        exitValue = round(exitPrice * numShares, 3)
        pnl       = round(numShares * (exitPrice - entryPrice), 3)
        pnlPct    = round(100 * pnl / abs(entryValue), 3) if entryValue != 0 else 0.0
        result.update({
            'exitDate':   closeDate,
            'exitPrice':  exitPrice,
            'exitValue':  exitValue,
            'pnl':        pnl,
            'pnlPercent': pnlPct,
        })

    return result

# Long position — win
def test_position_long_win():
    date      = datetime(1998, 1, 2)
    markDate  = datetime(1998, 1, 5)
    closeDate = datetime(1998, 1, 7)
    ex = _expected(date, "MSFT", 1, 1621, "long", markDate, closeDate)

    pos = Position(date, "MSFT", 1, 1621, "long")
    assert pos.ticker     == ex['ticker']
    assert pos.entryDate  == ex['entryDate']
    assert pos.direction  == ex['direction']
    assert np.isclose(pos.entryPrice, ex['entryPrice'])
    assert pos.weight     == ex['weight']
    assert np.isclose(pos.numShares, ex['numShares'])
    assert np.isclose(pos.entryValue, ex['entryValue'], rtol=1e-3)

    pos.markToMarket(markDate)
    assert pos.markedDate == pd.Timestamp(markDate)
    assert np.isclose(pos.markedPrice, ex['markPrice'])
    assert np.isclose(pos.markedValue, ex['markValue'], rtol=1e-3)
    assert np.isclose(pos.unrealizedPnl, ex['markUnrealizedPnl'], rtol=1e-3)
    assert np.isclose(pos.unrealizedPnlPercent, ex['markUnrealizedPct'], rtol=1e-3)

    pos.close(closeDate)
    assert pos.exitDate == ex['exitDate']
    assert np.isclose(pos.exitPrice, ex['exitPrice'])
    assert np.isclose(pos.exitValue, ex['exitValue'], rtol=1e-3)
    assert np.isclose(pos.pnl, ex['pnl'], rtol=1e-3)
    assert np.isclose(pos.pnlPercent, ex['pnlPercent'], rtol=1e-3)


# Long position — loss
def test_position_long_loss():
    date = datetime(1998, 9, 30)
    markDate = datetime(1998, 10, 8)
    closeDate = datetime(1998, 10, 14)
    ex = _expected(date, "MSFT", 1, 2809, "long", markDate, closeDate)

    pos = Position(date, "MSFT", 1, 2809, "long")
    assert np.isclose(pos.numShares, ex['numShares'])
    assert np.isclose(pos.entryValue, ex['entryValue'], rtol=1e-3)

    pos.markToMarket(markDate)
    assert np.isclose(pos.markedValue, ex['markValue'], rtol=1e-3)
    assert np.isclose(pos.unrealizedPnl, ex['markUnrealizedPnl'], rtol=1e-3)

    pos.close(closeDate)
    assert np.isclose(pos.pnl, ex['pnl'], rtol=1e-3)
    assert np.isclose(pos.pnlPercent, ex['pnlPercent'], rtol=1e-3)


# Short position — win
def test_position_short_win():
    date = datetime(2025, 3, 24)
    markDate = datetime(2025, 4, 3)
    closeDate = datetime(2025, 4, 21)
    ex = _expected(date, "AAPL", 1, 22100, "short", markDate, closeDate)

    pos = Position(date, "AAPL", 1, 22100, "short")
    assert pos.direction == "short"
    assert pos.numShares < 0
    assert np.isclose(pos.numShares, ex['numShares'])
    assert np.isclose(pos.entryValue, ex['entryValue'], rtol=1e-3)

    pos.markToMarket(markDate)
    assert np.isclose(pos.markedValue, ex['markValue'], rtol=1e-3)
    assert np.isclose(pos.unrealizedPnl, ex['markUnrealizedPnl'], rtol=1e-3)

    pos.close(closeDate)
    assert np.isclose(pos.pnl, ex['pnl'], rtol=1e-3)
    assert np.isclose(pos.pnlPercent, ex['pnlPercent'], rtol=1e-3)


# Short position — loss
def test_position_short_loss():
    date = datetime(2025, 4, 21)
    markDate = datetime(2025, 4, 28)
    closeDate = datetime(2025, 5, 2)
    ex = _expected(date, "AAPL", 1, 19327, "short", markDate, closeDate)

    pos = Position(date, "AAPL", 1, 19327, "short")
    assert pos.direction == "short"
    assert np.isclose(pos.numShares, ex['numShares'])

    pos.markToMarket(markDate)
    assert np.isclose(pos.markedValue, ex['markValue'], rtol=1e-3)
    assert np.isclose(pos.unrealizedPnl, ex['markUnrealizedPnl'], rtol=1e-3)

    pos.close(closeDate)
    assert np.isclose(pos.pnl, ex['pnl'], rtol=1e-3)


# Equality
def test_position_equals_type_error():
    pos = Position(datetime(1998, 1, 7), "MSFT", 1, 1754, "long")
    with pytest.raises(TypeError):
        pos == {"test": 0}


def test_position_equals_same():
    pos1 = Position(datetime(1998, 1, 7), "MSFT", 1, 1754, "long")
    pos2 = Position(datetime(1998, 1, 7), "MSFT", 1, 1754, "long")
    assert pos1 == pos2


def test_position_not_equals_different_weight():
    pos1 = Position(datetime(1998, 1, 7), "MSFT", 1,   1754, "long")
    pos2 = Position(datetime(1998, 1, 7), "MSFT", 0.5, 1754, "long")
    assert pos1 != pos2


def test_position_not_equals_different_mark():
    pos1 = Position(datetime(1998, 1, 7), "MSFT", 1, 1754, "long")
    pos2 = Position(datetime(1998, 1, 7), "MSFT", 1, 1754, "long")
    pos1.markToMarket(datetime(2025, 4, 21))
    pos2.markToMarket(datetime(2025, 4, 22))
    assert pos1 != pos2


def test_position_equals_after_same_mark():
    pos1 = Position(datetime(1998, 1, 7), "MSFT", 1, 1754, "long")
    pos2 = Position(datetime(1998, 1, 7), "MSFT", 1, 1754, "long")
    pos1.markToMarket(datetime(2025, 4, 21))
    pos2.markToMarket(datetime(2025, 4, 21))
    assert pos1 == pos2

# pytest -vv Tests/Position/TestPosition.py