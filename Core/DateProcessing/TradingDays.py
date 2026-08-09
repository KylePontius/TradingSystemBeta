import pandas_market_calendars as mcal
import numpy as np
import pandas as pd
from datetime import datetime

def getTradingDays(startDate : datetime, endDate : datetime) -> np.ndarray:
    '''
    Grabs the set of trading days between two days
    '''
    if not isinstance(startDate, (datetime, pd.Timestamp)):
        raise TypeError(f"Expected datetime or pd.Timestamp for startDate, got {type(startDate)}")
    if not isinstance(endDate, (datetime, pd.Timestamp)):
        raise TypeError(f"Expected datetime or pd.Timestamp for endDate, got {type(endDate)}")
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=startDate, end_date=endDate)
    return schedule.index.to_pydatetime()

def getFirstAndLast(tradingDays : np.ndarray) -> pd.DataFrame:
    '''Find the first and last trading day from a set of trading days'''
    if not isinstance(tradingDays, (np.ndarray, pd.DatetimeIndex)):
        raise TypeError(f"Expected tradingDays to be an np.ndarry or pd.DatetimeIndex, got {type(tradingDays)}.")
    tradingDays = pd.to_datetime(tradingDays)
    tradingDays = tradingDays.sort_values()

    df = pd.DataFrame({"date": tradingDays})
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    grouped = df.groupby(["year", "month"])["date"].agg(["first", "last"]).reset_index()
    grouped["first"] = pd.to_datetime(grouped["first"]).dt.normalize()
    grouped["last"]  = pd.to_datetime(grouped["last"]).dt.normalize()
    return grouped

def getLatestTradingDay(date : datetime, tradingDays : np.ndarray) -> datetime:
    '''Finds latest trading day given a set of trading days and a current date, critical for rebalance dates'''
    if not isinstance(date, (datetime, pd.Timestamp)):
        raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")
    if not isinstance(tradingDays, (np.ndarray, pd.DatetimeIndex)):
        raise TypeError(f"Expected np.ndarray or pd.DatetimeIndex for tradingDays, got {type(tradingDays)}.")
    tradingDays = pd.to_datetime(tradingDays)
    validDays = tradingDays[tradingDays <= pd.Timestamp(date)]
    if len(validDays) == 0:
        return None
    return validDays[-1].to_pydatetime()

def getNextTradingDay(date : datetime, tradingDays : np.ndarray) -> datetime:
    '''Finds the next trading day given a set of trading days and a current date, critical for execution dates'''
    if not isinstance(date, (datetime, pd.Timestamp)):
        raise TypeError(f"Expected datetime or pd.Timestamp for date, got {type(date)}")
    if not isinstance(tradingDays, (np.ndarray, pd.DatetimeIndex)):
        raise TypeError(f"Expected np.ndarray or pd.DatetimeIndex for tradingDays, got {type(tradingDays)}.")
    tradingDays = pd.to_datetime(tradingDays)
    validDays = tradingDays[tradingDays > pd.Timestamp(date)]
    if len(validDays) == 0:
        return None
    return validDays[0].to_pydatetime()

# def getLatestUniverseDate(date : pd.Timestamp, universe : pd.DataFrame) -> pd.Timestamp:
#     '''Given a universe and a date, find the latest date in which to consider said universe'''
#     if not isinstance(date, pd.Timestamp):
#         raise TypeError(f"Expected pd.Timestamp for date, got {type(date)}.")
#     if not isinstance(universe, pd.DataFrame):
#         raise TypeError(f"Expected pd.DataFrame for universe, got {type(universe)}.")
#     df = universe
#     df.columns = df.columns.str.strip()
#     df = df[(pd.to_datetime(df['date']) <= pd.to_datetime(date))]
#     series = df.iloc[-1]
#     date = series['date']
#     return date