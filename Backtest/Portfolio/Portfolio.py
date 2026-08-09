import pandas as pd
import numpy as np
from datetime import datetime
from Backtest.Position.Position import Position
from Backtest.Portfolio.PortfolioInterface import PortfolioInterface

class Portfolio(PortfolioInterface):
    def __init__(self, name : str, date : datetime, balance : float, endDate : datetime):
        '''
        Initializes a portfolio with the following:
        startDate: When portfolio was made
        endDate: When portfolio was set to expire
        startBalance: Initial balance of portfolio/account
        balance: Current balance of the account
        latestNav: A dictionary which has the initial date and NAV set to the given balance
        '''
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}.")
        if not isinstance(endDate, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime, pd.Timestamp for endDate, got {type(endDate)}")
        if not isinstance(balance, (float, np.float64, int)):  
            raise TypeError(f"Expected a float or int for balance, got {type(balance)}.")

        if endDate < date:
            raise ValueError("endDate cannot be sooner than startDate.")
        if balance <= 0:
            raise ValueError(f"Balance cannot be 0 or negative, got {balance}.")
        
        self.name = str(name)
        self.startDate = pd.Timestamp(date)
        self.endDate = pd.Timestamp(endDate)
        self.startBalance = balance
        self.balance = balance
        self.unrestrictedBalance = balance

        self.navHistory = {}
        self.holdings = []
        self.tradingHistory = []

        self.realizedPnl = 0

    def value(self, date: datetime) -> float:
        """Return NAV for date. Portfolio must already be marked to this date."""
        if pd.Timestamp(date) not in self.navHistory:
            raise ValueError(
                f'Portfolio {self.name} has no record for {pd.Timestamp(date)}.'
            )
        return self.navHistory[pd.Timestamp(date)]
    
    def markToMarket(self, date: datetime):
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}.")
        date = pd.Timestamp(date)

        if date in self.navHistory:
            return self  # already marked, skip silently

        if self.navHistory and date <= max(self.navHistory):
            raise ValueError(f"{date} has already occurred, cannot create NAV for a historical date.")
        
        for position in self.holdings:
            position.markToMarket(date)

        assetsWorth = sum(h.markedValue for h in self.holdings)
        nav = round(assetsWorth + self.balance, 10)
        self.navHistory[pd.Timestamp(date)] = nav

        return self
    
    def isExpired(self, date: datetime) -> bool:
        '''Checks if the portfolio is expired on a given date.'''
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}.")
        return pd.Timestamp(date) >= self.endDate    
    
    def enterPosition(self, date : datetime, ticker : str, weight : float,
                    allocation : float, direction : str):
        '''Inititiates a single position by buying and adding said position to holdings.'''
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}.")
        if not isinstance(ticker, str):
            raise TypeError(f"Expected str for ticker, got {type(ticker)}.")
        if not isinstance(weight, (float, int, np.float64)):
            raise TypeError(f"Expected float, int, or np.float64 for weight, got {type(weight)}.")
        if not isinstance(allocation, (float, int, np.float64)):
            raise TypeError(f"Expected float, int, or np.float64 for weight, got {type(allocation)}.")
        if not isinstance(direction, str):
            raise TypeError(f"Expected str for ticker, got {type(direction)}.")
        position = Position(date, ticker, weight, allocation, direction)
        if abs(position.entryValue) > self.unrestrictedBalance:
            raise ValueError("Insufficient unrestricted capital.")
        if self.navHistory and date < max(self.navHistory):
            raise ValueError(f"{date} has already occurred, cannot enter position for a historical date.")        

        self.balance = round(self.balance - position.entryValue, 10)
        self.unrestrictedBalance = round(self.unrestrictedBalance - abs(position.entryValue), 10)
        self.holdings.append(position)

        return self
    
    def enterPositions(self, date: datetime, positions: list):
        '''Initiates multiple positions simultaneously.
        Expects positions as list of (ticker, weight, direction, slippage).
        Capital is allocated equally across slots based on pre-entry unrestricted balance.
        '''
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}.")
        if not positions:
            raise ValueError("positions list cannot be empty.")

        date = pd.Timestamp(date)

        slotSize      = self.unrestrictedBalance / len(positions)
        totalInvested = 0
        totalConsumed = 0

        for ticker, weight, direction, slippage in positions:
            allocation = slotSize * weight
            if allocation <= 0:
                continue
            totalConsumed += abs(allocation)

        if totalConsumed > self.unrestrictedBalance + 1e-9:
            raise ValueError('The total sum of weight values causes allocations greater than possible.')

        potentialPositions = []

        for ticker, weight, direction, slippage in positions:
            allocation = slotSize * weight
            if allocation <= 0:
                continue

            position = Position(date, ticker, weight, allocation, direction, slippage)
            potentialPositions.append(position)
            totalInvested += position.entryValue

        self.holdings.extend(potentialPositions)

        self.balance             = round(self.balance - totalInvested, 10)
        self.unrestrictedBalance = round(self.unrestrictedBalance - totalConsumed, 10)
        return self