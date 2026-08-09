import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from Backtest.AssetInteractions.Weigh import *

@pytest.mark.parametrize(
    'date,ticker,mode,size',
    [
        (0, "MSFT", "EQUAL", 20),
        (datetime(2025,5,31), 0, "EQUAL", 20),
        (datetime(2025,5,31), "MSFT", 0, 20),
        (datetime(2025,5,31), "MSFT", 0, ""),
    ]
)
def test_weigh_failed_types(date, ticker, mode, size):
    with pytest.raises(TypeError):
        weigh(date, ticker, mode, size)

@pytest.mark.parametrize(
    'date,ticker,mode,size',
    [
        (datetime(2025,5,31), "MSFT", '0', 5),
        (datetime(2025,5,31), "MSFT", 'EQUAL', -5),
    ]
)
def test_weigh_failed_value(date, ticker, mode, size):
    with pytest.raises(ValueError):
        weigh(date, ticker, mode, size)

expected = .2
@pytest.mark.parametrize(
    'date,ticker,mode,size',
    [
        (datetime(2025,5,31), "MSFT", "EQUAL", 5)
    ]
)
def test_weigh_sucess(date, ticker, mode, size):
    assert weigh(date, ticker, mode, size) == .2

#pytest Tests/AssetInteractions/TestWeigh.py