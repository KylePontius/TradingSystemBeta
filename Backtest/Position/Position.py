import numpy as np
import pandas as pd
from datetime import datetime

from Backtest.AssetInteractions.Prices import getOpen, getAdjustedClose
from Backtest.AssetInteractions.MarketCap import getMarketCap
from Core.Config.specs.slippage import SlippageSpec


class Position:
    def __init__(
        self,
        date:       datetime,
        ticker:     str,
        weight:     float,
        allocation: float,
        direction:  str,
        slippage:   SlippageSpec = SlippageSpec(model='none'),
    ):
        # Type validation
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")
        if not isinstance(ticker, str):
            raise TypeError(f"Expected str for ticker, got {type(ticker)}")
        if not isinstance(weight, (float, int, np.float64)):
            raise TypeError(f"Expected float/int/np.float64 for weight, got {type(weight)}")
        if not isinstance(allocation, (float, int, np.float64)):
            raise TypeError(f"Expected float/int/np.float64 for allocation, got {type(allocation)}")
        if not isinstance(direction, str):
            raise TypeError(f"Expected str for direction, got {type(direction)}")

        # Value validation
        if direction.lower() not in ['long', 'short']:
            raise ValueError(f"Invalid direction {direction}, must be 'long' or 'short'.")
        if weight < 0:
            raise ValueError("Weight cannot be negative. Use direction 'short' instead.")
        if allocation < 0:
            raise ValueError("allocation cannot be negative.")

        # Metadata
        self.ticker    = ticker
        self.direction = direction.lower()
        self.slippage  = slippage

        # Entry
        self.entryDate = date
        rawEntryPrice  = getOpen(date, ticker)
        marketCap      = getMarketCap(date, ticker)

        # Apply slippage to entry price
        self.entryPrice = slippage.adjustEntry(rawEntryPrice, marketCap, self.direction)

        self.weight    = weight
        self.numShares = (allocation * weight) / self.entryPrice
        if self.direction == 'short':
            self.numShares = -self.numShares

        self.entryValue = round(self.numShares * self.entryPrice, 3)

        # Initial mark (use adjusted close for P&L tracking)
        self.markedDate  = date
        self.markedPrice = getAdjustedClose(date, ticker)
        self.markedValue = round(self.numShares * self.markedPrice, 3)

        self.unrealizedPnl = self.markedValue - self.entryValue
        self.unrealizedPnlPercent = (
            round(100 * self.unrealizedPnl / abs(self.entryValue), 3)
            if self.entryValue != 0 else 0.0
        )

        # Exit (populated on close)
        self.exitDate  = None
        self.exitPrice = None
        self.exitValue = None
        self.pnl       = 0
        self.pnlPercent = 0

    def markToMarket(self, date: datetime):
        """Update position value for a given date using adjusted close."""
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")

        try:
            self.markedPrice = getAdjustedClose(date, self.ticker)
        except ValueError:
            # No price data — ticker likely delisted, freeze at last known price
            pass

        self.markedDate  = date
        self.markedValue = round(self.numShares * self.markedPrice, 3)

        if self.entryValue != 0:
            self.unrealizedPnl        = round(self.markedValue - self.entryValue, 3)
            self.unrealizedPnlPercent = round(
                100 * self.unrealizedPnl / abs(self.entryValue), 3
            )
        return self

    def close(self, date: datetime):
        """Close the position at a given date using raw open price."""
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")

        # Get raw exit price — fall back to last marked price if delisted
        try:
            rawExitPrice = getOpen(date, self.ticker)
        except ValueError:
            rawExitPrice = self.markedPrice

        # Get market cap for slippage (use entry date cap — close enough)
        marketCap = getMarketCap(self.entryDate, self.ticker)

        # Apply slippage to exit price
        self.exitPrice  = self.slippage.adjustExit(rawExitPrice, marketCap, self.direction)
        self.exitDate   = date
        self.markedPrice = self.exitPrice
        self.exitValue  = round(self.exitPrice * self.numShares, 3)
        self.markedValue = self.exitValue

        self.pnl = round(self.numShares * (self.exitPrice - self.entryPrice), 3)
        self.pnlPercent = (
            round(100 * self.pnl / abs(self.entryValue), 3)
            if self.entryValue != 0 else 0.0
        )
        return self

    def __eq__(self, other):
        if not isinstance(other, Position):
            raise TypeError(f"Expected Position for other, got {type(other)}.")

        tol = 1e-3

        def approx(a, b):
            if a is None or b is None:
                return a == b
            return np.isclose(a, b, rtol=tol)

        return (
            self.ticker == other.ticker
            and self.direction == other.direction
            and self.entryDate == other.entryDate
            and approx(self.entryPrice, other.entryPrice)
            and approx(self.entryValue, other.entryValue)
            and approx(self.numShares, other.numShares)
            and approx(self.markedPrice, other.markedPrice)
            and approx(self.markedValue, other.markedValue)
            and approx(self.unrealizedPnl, other.unrealizedPnl)
            and approx(self.pnl, other.pnl)
        )