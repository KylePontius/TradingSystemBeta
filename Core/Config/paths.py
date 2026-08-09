import os
from pathlib import Path

BASE = Path(os.environ.get("TRADING_SYSTEM_ROOT", Path(__file__).resolve().parents[2]))

FACTORS_DIR = BASE / "Data" / "Factors"
SIGNALS_DIR = BASE / "Data" / "Signals"
UNIVERSE_DIR = BASE / "Data" / "Universe"
STOCK_DIR    = BASE / "Data" / "Stocks"
CONFIGS_DIR  = BASE / "Configs"
SHARADAR_DIR = BASE / "Data" / "Sharadar"
BENCHMARKS_DIR = BASE / "Data" / "Benchmarks"