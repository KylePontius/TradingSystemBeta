from datetime import datetime
import numpy as np
import polars as pl
from pathlib import Path

BASE = Path("C:/Users/Kyle/.vscode/projects/TradingSystem/StockData")

def weigh(
        date : datetime,
        ticker : str,
        mode : str,
        size : int = 0) -> float:
    if not isinstance(date, datetime):
        raise TypeError(f"Expected datetime for date, got {type(date)}")
    if not isinstance(ticker, str):
        raise TypeError(f"Expected str for ticker, got {type(ticker)}")
    if not isinstance(mode, str):
        raise TypeError(f"Expected str for mode, got {type(mode)}")
    if not isinstance(size, int):
        raise TypeError(f"Expected int for size, got {type(size)}")
    if size <= 0:
        raise ValueError(f"Error, size must be a positive integer, got {size}")
    
    validModes = ['equal']
    mode = mode.lower()
    if mode not in validModes:
        raise ValueError(f"{mode} is not a valid mode, must be one of the modes in {validModes}.")
    if mode == "equal":
        return 1 / size