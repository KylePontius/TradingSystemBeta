import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from Backtest.Portfolio.Portfolio import Portfolio
from Backtest.AssetInteractions.Prices import *
from Core.Config.specs.slippage import SlippageSpec

@pytest.mark.parametrize(
    "name,date,balance,endDate",
    [
        ('test', 0, 100000, None),
        ('test', pd.Timestamp("2025-05-30"), "", None),
        ('test', datetime(2025, 5, 30), 100000, ""),
    ]
)
def test_Portfolio_invalid_types(name, date, balance, endDate):
    with pytest.raises(TypeError):
        Portfolio(name, date, balance, endDate)

@pytest.mark.parametrize(
    "name,date,balance,endDate",
    [
        ('test', pd.Timestamp("2025-05-30"), -100000, pd.Timestamp("2025-05-31")),
        ('test', pd.Timestamp("2025-05-30"), 10000, pd.Timestamp("2025-05-29")),
        ('test', datetime(2025, 5, 30), 1, datetime(2025, 5, 29))
    ]
)
def test_Portfolio_invalid_values(name, date, balance, endDate):
    with pytest.raises(ValueError):
        Portfolio(name, date, balance, endDate)

@pytest.mark.parametrize(
    "name,date,balance,endDate",
    [
        ('test', pd.Timestamp("2025-05-30"), 100000, pd.Timestamp("2025-05-31")),
    ]
)
def test_Portfolio_invalid_navHistory_value(name, date, balance, endDate):
    portfolio = Portfolio(name, date, balance, endDate)
    positions = [
        ("MSFT", 1, "long", SlippageSpec('none')),
        ("AAPL", 1, "short", SlippageSpec('none')),
        ("PLTR", 1, "long", SlippageSpec('none')),
    ]
    portfolio.enterPositions(date, positions)
    portfolio.markToMarket(date)
    with pytest.raises(ValueError):
        portfolio.markToMarket(date)

@pytest.fixture
def portfolio():
    """Creates a fresh portfolio"""

    name = "test"
    startDate = pd.Timestamp("2025-03-21")
    endDate = pd.Timestamp("2025-03-31")
    balance = 75000

    return Portfolio(name, startDate, balance, endDate)


def test_portfolio_full_flow(portfolio: Portfolio):
    """Behavioral test of portfolio from entry through NAV updates and exit."""
    startDate = pd.Timestamp("2025-03-21")
    midDate1 = pd.Timestamp("2025-03-24")
    midDate2 = pd.Timestamp("2025-03-28")
    endDate = pd.Timestamp("2025-03-31")

    assert portfolio.name == "test"
    assert portfolio.balance == 75000
    assert portfolio.unrestrictedBalance == 75000
    assert portfolio.holdings == []
    assert portfolio.navHistory == {}
    assert portfolio.realizedPnl == 0

    positions = [
        ("MSFT", 1, "long", SlippageSpec('none')),
        ("AAPL", 1, "short", SlippageSpec('none')),
        ("PLTR", 1, "long", SlippageSpec('none')),
    ]
    portfolio.enterPositions(startDate, positions)

    totalEntry = sum(h.entryValue for h in portfolio.holdings)
    assert portfolio.unrestrictedBalance >= 0
    assert np.isclose(portfolio.startBalance, portfolio.balance + totalEntry, rtol=1e-5)

    portfolio.markToMarket(startDate)
    assert len(portfolio.navHistory) == 1
    assert portfolio.navHistory[startDate] == 101218.155 - 25000

    oldNav = portfolio.navHistory[startDate]
    portfolio.markToMarket(midDate1)
    assert np.isclose(
        portfolio.navHistory[midDate1],
        portfolio.balance + sum(h.markedValue for h in portfolio.holdings),
        rtol=1e-5
    )
    assert len(portfolio.navHistory) == 2
    assert midDate1 in portfolio.navHistory
    assert all(h.markedDate == midDate1 for h in portfolio.holdings)
    assert portfolio.navHistory[midDate1] != oldNav

    toClose = portfolio.holdings[0]
    preBalance = portfolio.balance
    portfolio.exitPosition(midDate2, toClose)
    assert np.isclose(
        portfolio.balance,
        preBalance + toClose.exitValue,
        rtol=1e-5
    )
    assert len(portfolio.holdings) == 2
    assert len(portfolio.tradingHistory) == 1
    assert portfolio.tradingHistory[0].exitDate == midDate2
    assert portfolio.balance != preBalance
    assert isinstance(portfolio.realizedPnl, float)

    portfolio.markToMarket(midDate2)
    assert midDate2 in portfolio.navHistory
    assert np.isclose(
        portfolio.navHistory[midDate2],
        portfolio.balance + sum(h.markedValue for h in portfolio.holdings),
        rtol=1e-5
    )
    assert np.isclose(
        portfolio.navHistory[midDate2],
        preBalance + toClose.exitValue + sum(h.markedValue for h in portfolio.holdings) 
    )

    portfolio.exitAllPositions(endDate)
    assert len(portfolio.holdings) == 0
    assert len(portfolio.tradingHistory) == 3
    assert all(p.exitDate is not None for p in portfolio.tradingHistory)

    portfolio.markToMarket(endDate)
    final_nav = portfolio.navHistory[endDate]
    assert np.isclose(final_nav, portfolio.balance, rtol=1e-7)
    assert portfolio.isExpired(endDate)

    totalRealized = sum(p.pnl for p in portfolio.tradingHistory)
    assert np.isclose(totalRealized, portfolio.realizedPnl, rtol=1e-5)

#pytest -vv Tests/Portfolio/TestPortfolio.py

