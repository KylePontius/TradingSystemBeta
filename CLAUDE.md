# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run a backtest:**
```bash
python test_run.py
```

**Run IC (Information Coefficient) analysis:**
```bash
python research_run.py
```

**Run all tests:**
```bash
pytest Tests/
```

**Run a single test file:**
```bash
pytest Tests/TestPosition.py
```

## Architecture Overview

This is a Python quantitative trading backtest system. The data flow is:

```
YAML Config → BacktestSpec → Signal Pipeline → Simulation → MasterPortfolio
```

### Config Layer (`Core/Config/`)

`loader.py` parses a YAML config into a frozen `BacktestSpec` dataclass. All sub-configs (factors, universe, signals, strategy) become typed frozen dataclasses in `Core/Config/specs/`. These specs are immutable and passed through the system.

### Signal Pipeline (`Core/Signals/`, `Core/Factors/`, `Core/Universe/`)

`signalEngine.ensure(spec)` computes a signal artifact via this pipeline:
1. Load universe (e.g., Russell3000) via `UniverseEngine`
2. Compute factors (e.g., residual_momentum) via `FactorEngine`
3. Normalize cross-sectionally (zscore/rank + optional winsorize)
4. Combine factors (none/equal/linear/ridge)
5. Rank and select long/short tickers

Output: a parquet of `date | ticker | signal | score | rank`

**Caching:** All artifacts use content-hash naming (`spec_hash()`). Each spec's `identity()` method defines what's hashed. Cache files live in `Data/Factors/`, `Data/Signals/`, `Data/Universe/`. A cache hit skips recomputation entirely.

### Backtest Simulation (`Backtest/Simulation/`)

`Simulate.run(configPath)` is the main entry point. It builds a monthly formation schedule and for each formation date:
1. Marks MasterPortfolio to market
2. Exits expired cohorts (`Rebalance.py`)
3. Loads signals, builds new positions (`Execute.py`)
4. Computes capital allocation (`Accounting.py`)
5. Creates a new `Portfolio` (cohort) and adds it to `MasterPortfolio`

### Portfolio Model (`Backtest/Portfolio/`, `Backtest/Position/`)

**MasterPortfolio** — portfolio-of-portfolios; holds multiple active `Portfolio` cohorts simultaneously.

**Portfolio** — a single cohort (e.g., "Jan 2023 formation") holding positions for `holdingPeriods` months.

**Position** — a single stock holding. Entry price has slippage applied via `slippage.adjustEntry(price, marketCap, direction)`. Mark-to-market uses adjusted close. Supports fractional shares.

Capital allocation: `equalSplit` divides NAV by `holdingPeriods`, so 1/N of capital is deployed each formation period.

### Data Sources

- **Prices:** `Data/Stocks/ticker={ticker}.parquet` — OHLCV with adjusted close
- **Fundamentals:** `Data/Sharadar/SF1.parquet`, `Data/Sharadar/SEP.parquet`
- **Benchmarks:** `Data/Benchmarks/`
- **Universe:** `Data/Universe/Russell3000.parquet` (base list)

All price/market cap lookups go through `Backtest/AssetInteractions/Prices.py` and `MarketCap.py`. Market cap tiers drive slippage: large ≥$10B (5bps), mid ≥$2B (10bps), small ≥$300M (20bps), micro (40bps).

### Key Conventions

- **Polars** throughout (lazy frames via `.scan_parquet()`, collected at output)
- **Frozen dataclasses** for all specs — never mutate
- **`ResearchClaude/`** is the active research folder — never read from `Research/`
- `Core/Config/paths.py` is the single source of truth for all file paths