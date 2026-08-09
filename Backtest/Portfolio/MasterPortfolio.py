import pandas as pd
import numpy as np
from datetime import datetime
from Backtest.Portfolio.PortfolioInterface import PortfolioInterface
from Backtest.Portfolio.Portfolio import Portfolio

class MasterPortfolio(PortfolioInterface):
    """
    A Portfolio-of-Portfolios.
    Implements the PortfolioInterface so simulation code
    can treat MasterPortfolio just like a Portfolio.
    """
    def __init__(self, name: str, startDate: datetime, balance: float):
        if balance <= 0:
            raise ValueError("Balance must be positive.")
        if not isinstance(startDate, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(startDate)}.")
        if not isinstance(balance, (float, np.float64, int)):  
            raise TypeError(f"Expected a float or int for balance, got {type(balance)}.")
        
        self.name = str(name)
        self.startDate = pd.Timestamp(startDate)
        self.startBalance = balance
        self.balance = balance

        self.portfolios = []
        self.navHistory = {self.startDate : self.balance}
        self.latestNavDate = self.startDate
        self.tradingHistory = []

        self.realizedPnl = 0

        self._bootstrap_nav_active = True
        
    def value(self, date : datetime):
        if pd.Timestamp(date) not in self.navHistory:
            raise ValueError(
                f'Portfolio {self.name} has no record for {pd.Timestamp(date)}.'
            )
        return self.navHistory[pd.Timestamp(date)]
    
    def markToMarket(self, date : datetime):
        '''For a given date find the date's NAV 
        and append it to the navHistory, and sets the latestNavDate'''
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}.")
        
        date = pd.Timestamp(date)
        if date < self.latestNavDate:
                raise ValueError("Cannot mark NAV in the past.")

        if date == self.latestNavDate:
            if not (self._bootstrap_nav_active and date == self.startDate):
                raise ValueError("Master NAV already exists for this date.")
            else:
                self._bootstrap_nav_active = False

        for portfolio in self.portfolios:
            portfolio.markToMarket(date)

        portfoliosWorth = sum(portfolio.value(date) for portfolio in self.portfolios)
        nav = round(portfoliosWorth + self.balance, 10)
        self.navHistory[pd.Timestamp(date)] = nav
        self.latestNavDate = date
        return self
    
    def addPortfolio(self, name: str, date: datetime, positions: list[tuple], 
                     allocation: float, endDate: datetime = None, allocationType: str = "fraction"):
        if not isinstance(date, (datetime, pd.Timestamp)):
            raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}.")
        date = pd.Timestamp(date)
        if date < self.latestNavDate:
            raise ValueError("Cannot add portfolio in the past.")
        
        if allocationType == 'fraction':
            if not (0 <= allocation <= 1):
                raise ValueError(f'For allocationType: fraction, requires [0,1].')
            capital = self.navHistory[self.latestNavDate] * allocation
        elif allocationType == 'absolute':
            capital = allocation
        else:
            raise ValueError("allocationType must be 'fraction' or 'absolute'")

        if capital > self.balance:
            raise ValueError("Not enough master capital.")

        portfolio = Portfolio(name, date, capital, endDate)
        portfolio = portfolio.enterPositions(date, positions)
        self.portfolios.append(portfolio)

        self.balance -= capital
        return self
    
    def exitPortfolio(self, date : datetime, portfolio : Portfolio):
        if portfolio not in self.portfolios:
            raise ValueError("Portfolio not managed in portfolios.")
        date = pd.Timestamp(date)
        portfolio.exitAllPositions(date)
        portfolio.markToMarket(date)
        self.balance += portfolio.value(date)
        self.realizedPnl += portfolio.realizedPnl

        self.portfolios.remove(portfolio)
        self.tradingHistory.append(portfolio)

        return self
