import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from Backtest.Portfolio.MasterPortfolio import MasterPortfolio
from Backtest.AssetInteractions.Prices import *
from Core.Config.specs.slippage import SlippageSpec

@pytest.mark.parametrize(
    "name,date,balance",
    [
        ('test', 0, 100000),
        ('test', pd.Timestamp("2025-05-30"), ""),
    ]
)
def test_Portfolio_invalid_types(name, date, balance):
    with pytest.raises(TypeError):
        MasterPortfolio(name, date, balance)

@pytest.mark.parametrize(
    "name,date,balance",
    [
        ('test', pd.Timestamp("2025-05-30"), -1),
    ]
)
def test_Portfolio_invalid_values(name, date, balance):
    with pytest.raises(ValueError):
        MasterPortfolio(name, date, balance)

@pytest.fixture
def portfolio():
    """Creates a fresh master portfolio"""

    name = "test"
    startDate = pd.Timestamp("2025-03-21")
    balance = 150000

    return MasterPortfolio(name, startDate, balance)

def test_master_bootstrap_nav():
    start = datetime(2025, 1, 2)
    mp = MasterPortfolio("master", start, 100000)

    assert mp.value(start) == 100000
    assert mp.latestNavDate == start

def test_one_off_eod_mark_start_date():
    start = datetime(2025, 1, 2)
    mp = MasterPortfolio("master", start, 100000)
    mp.markToMarket(start)  # allowed once

    with pytest.raises(ValueError):
        mp.markToMarket(start)  # second time forbidden

def test_invalid_mark_date_past():
    start = datetime(2025, 1, 2)
    later = datetime(2025, 1, 3)

    mp = MasterPortfolio("master", start, 100000)
    mp.markToMarket(start)
    mp.markToMarket(later)

    with pytest.raises(ValueError):
        mp.markToMarket(start)

def test_mark_to_market_monotonic():
    start = datetime(2025, 1, 2)
    d1 = datetime(2025, 1, 3)
    d2 = datetime(2025, 1, 4)

    mp = MasterPortfolio("master", start, 100_000)
    mp.markToMarket(start)
    mp.markToMarket(d1)
    mp.markToMarket(d2)

    assert mp.latestNavDate == d2
    assert list(mp.navHistory.keys()) == [start, d1, d2]


def test_fractional_allocation_reduces_cash(monkeypatch):
    start = datetime(2025, 1, 2)
    mp = MasterPortfolio("master", start, 100_000)
    mp.markToMarket(start)

    class DummyPortfolio:
        def __init__(self, name, date, capital, endDate):
            self.capital = capital
            self.realizedPnl = 0

        def enterPositions(self, *args, **kwargs):
            return self

        def exitAllPositions(self, *args, **kwargs):
            pass

        def markToMarket(self, *args, **kwargs):
            pass

        def value(self, *args, **kwargs):
            return self.capital

    monkeypatch.setattr(
        "Backtest.Portfolio.MasterPortfolio.Portfolio",
        DummyPortfolio
    )

    mp.addPortfolio(
        name="child",
        date=start,
        positions=[],
        allocation=0.2,
        allocationType="fraction"
    )

    assert mp.balance == 80000

def test_exit_returns_capital(monkeypatch):
    start = datetime(2025, 1, 2)
    mp = MasterPortfolio("master", start, 100000)
    mp.markToMarket(start)

    class DummyPortfolio:
        def __init__(self, name, date, capital, endDate):
            self.capital = capital
            self.realizedPnl = 5000

        def enterPositions(self, *args, **kwargs):
            return self

        def exitAllPositions(self, *args, **kwargs):
            pass

        def markToMarket(self, *args, **kwargs):
            pass

        def value(self, *args, **kwargs):
            return self.capital + 5000

    monkeypatch.setattr(
        "Backtest.Portfolio.MasterPortfolio.Portfolio",
        DummyPortfolio
    )

    p = mp.addPortfolio(
    name="child",
    date=start,
    positions=[],
    allocation=50000,
    allocationType="absolute"
    )

    # The child portfolio is stored here
    child = mp.portfolios[0]

    mp.exitPortfolio(start, child)

    assert mp.balance == 105000
    assert mp.realizedPnl == 5000
    assert len(mp.portfolios) == 0

def test_master_with_two_real_portfolios():

    start = datetime(2025, 3, 21)
    d1 = datetime(2025, 3, 24)
    d2 = datetime(2025, 3, 28)
    d3 = datetime(2025, 3, 31)
    master = MasterPortfolio("master", start, 100000)

    assert master.navHistory
    assert master.navHistory[start] == 100000

    # Portfolio 1
    positions1 = [
        ("MSFT", 1.0, "long", SlippageSpec('none')),
        ("AAPL", 1.0, "short", SlippageSpec('none')),
    ]

    master.addPortfolio(
        name="p1",
        date=start,
        positions=positions1,
        allocation=0.5,
        allocationType="fraction",
        endDate=d3
    )

    # Portfolio 2
    positions2 = [
        ("PLTR", 1.0, "long", SlippageSpec('none')),
    ]

    master.addPortfolio(
        name="p2",
        date=start,
        positions=positions2,
        allocation=0.25,
        allocationType="fraction",
        endDate=d3
    )

    # Capital should be reduced
    assert master.balance > 0
    assert len(master.portfolios) == 2
    master.markToMarket(start)
    assert master.navHistory[start] == 101218.155

    master.markToMarket(d1)
    assert master.navHistory[d1] == sum(p.navHistory[d1] for p in master.portfolios) + master.balance 
    master.markToMarket(d2)
    assert master.navHistory[d2] == sum(p.navHistory[d2] for p in master.portfolios) + master.balance 

    masterBalancePreExit = master.balance

    portfolioCashPreExit = sum(portfolio.balance for portfolio in master.portfolios)
    # Exit both portfolios on d3
    for p in master.portfolios[:]:
        master.exitPortfolio(d3, p)
    master.markToMarket(d3)

    expected = sum(
        sum(
            position.exitValue for position in portfolio.tradingHistory
        ) for portfolio in master.tradingHistory
    ) + masterBalancePreExit + portfolioCashPreExit
    
    assert master.value(d3) == expected

    assert len(master.portfolios) == 0

    assert master.value(d3) == pytest.approx(master.balance, rel=1e-6)


#pytest -vv Tests/Portfolio/TestMasterPortfolio.py