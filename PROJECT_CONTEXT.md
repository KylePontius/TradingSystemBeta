# TradingSystem — Project Context Document
# Last updated: March 25, 2026 (Redacted Items on 8/9/2026)

---

## Project Overview

Building a quantitative trading system in Python for Research.
Research -> Backtest -> Forward Test -> Paper Trade -> Live.
Universe: Russell 3000. Data: Sharadar (SF1 fundamentals, SEP pricing).
Stack: Polars, pandas, pandas_market_calendars, pytest, Jupyter.

---

## Project Structure

```
TradingSystem/
├── Core/
│   ├── Config/
│   │   ├── loader.py              # YAML -> BacktestSpec parser (supports direction field)
│   │   ├── paths.py               # centralized paths
│   │   ├── utils.py               # spec_hash (content hashing)
│   │   └── specs/
│   │       ├── backtest.py, run.py, signal.py, universe.py
│   │       ├── factor.py           # FactorSpec with direction field (1 or -1)
│   │       ├── filter.py, selection.py
│   │       ├── normalize.py
│   │       ├── combine.py   
│   │       ├── ranking.py
│   │       ├── forward_return.py
│   │       ├── strategy.py, capital.py, position.py
│   │       └── slippage.py
│   ├── Factors/
│   │   ├── FactorEngine.py        # compute+cache factors as parquet
│   │   ├── ForwardReturns.py      # compute+cache forward returns
│   │   └── generators/
│   │       ├── momentum.py        # log return: log(P[t-buffer]) - log(P[t-lookback])
│   │       ├── volatility.py      # rolling std of log returns, annualized
│   │       ├── jtVolatility.py
│   │       ├── residualMomentum.py
│   │       └── value.py           # composite: FCF yield, earnings yield, B/M (z-scored)
│   ├── Signals/
│   │   └── signalEngine.py        # unified signal pipeline (direction)
│   ├── Universe/
│   │   ├── UniverseEngine.py
│   │   └── masterUniverse.py
│   └── DateProcessing/
│       └── TradingDays.py
│   Models/                        # NEXT PHASE — REDACTED
│   ├── REDACTED/
├── Backtest/
│   ├── Portfolio/
│   │   ├── MasterPortfolio.py
│   │   ├── Portfolio.py
│   │   └── PortfolioInterface.py
│   ├── Position/
│   │   └── Position.py
│   ├── AssetInteractions/
│   │   ├── Prices.py
│   │   └── MarketCap.py
│   └── Simulation/
│       ├── Simulate.py
│       ├── Rebalance.py
│       ├── Execute.py
│       └── Accounting.py
├── Configs/
│   └── example.yaml
├── Data/
│   ├── Stocks/ticker=*/0.parquet  # SEP price data partitioned by ticker
│   ├── Sharadar/sharadarSF1.csv
│   ├── Factors/                   # cached factor parquets (content-hashed)
│   ├── Signals/                   # cached signal parquets
│   ├── Universe/                  # cached universe parquets
│   └── Posteriors/                # PLANNED
├── Research/
│   ├── Tools/
│   │   ├── ic.py
│   │   └── results.py
│   └── Notebooks/
│       ├── momentum_research.ipynb
│       └── momentum_variants.ipynb
└── Tests/
    └── Position/
        └── TestPosition.py
```

---

## Key Design Decisions

**Simulation style:** Rolling cohort (Jegadeesh-Titman style)
- Monthly formation frequency
- Each cohort is an independent Portfolio held for 6 months max
- MasterPortfolio manages all active cohorts (up to 6 at a time)
- 20 positions per cohort, ~120 max active positions across cohorts

**Position:** Fractional shares

**Slippage:** Size-based bid-ask spread
- Large cap >$10B: 5bps per side
- Mid cap $2B-$10B: 10bps per side
- Small cap $300M-$2B: 20bps per side
- Micro cap <$300M: 40bps per side

**Prices:**
- Entry/exit: raw open price (getOpen)
- Mark-to-market: adjusted close (getAdjustedClose) for correct P&L

**Caching:** Content-hash based (spec_hash) — factors, signals, universe, posteriors all cached by config hash.

**Version control:** Git initialized. Commit before any changes.

---

## Factor Direction Convention

FactorSpec has a `direction` field (1 or -1, default 1).
- `direction=1`: higher raw value = better (momentum, value)
- `direction=-1`: higher raw value = worse, flip sign after normalization (volatility)
- Applied in signalEngine section 4 after z-scoring: `x = x * factor.direction`
- Included in `identity()` only when != 1 (to preserve backward cache compatibility)

---

## Russell 3000 Universe — CRITICAL

The universe parquet (`Data/Universe/Russell3000.parquet`) must be generated using the OLD `createUniverseByMarketCap` script, NOT the newer `buildRussell3000` script. The newer script produces a different universe composition (only 57% overlap per date) which dramatically changes backtest results. The difference is the old script uses ALL SF1 dimensions for market cap forward-fill, while the new script filters to ARQ only, dropping tickers with only annual reports.

The old script is slow (ticker-by-ticker loop) but functionally correct — no lookahead bias. Optimization should preserve identical output.

**Always verify the universe parquet is from the correct build script before running backtests.** A wrong universe silently produces drastically different (and wrong) results with no errors.

---
## Alpha Results

```
Best Alpha Found:
Blend      CAGR:  14.58%  Sharpe: 0.790  MaxDD: -39.36%
SPY        CAGR:  11.57%  Sharpe: 0.726  MaxDD: -34.10%
```

---

## Backtest Results

### Dual Momentum - Residual Momentum (252-21) >= 0 & Residual Momentum (126-21) - Low Volatility (126-0) - Value - Russell 3000 - 12 Months
```
Period               2010-01-04 to 2024-12-31
Starting Capital                $  100,000.00
Final NAV                       $  553,793.09
Total Return                          453.79%
CAGR                                   12.10%
Sharpe Ratio                            0.574
Volatility (ann.)                      15.35%
Max Drawdown                          -39.43%
Cohorts Traded                            180
Win Rate                               80.00%
Avg Cohort Return                      12.68%
Realized P&L                    $  449,535.40
```

### Dual Momentum - Residual Momentum (252-21) >= 0 & Residual Momentum (126-21) - Low Volatility (126-0) - Value - Russell 3000 - 6 Months
```
Period               2010-01-04 to 2024-12-31
Starting Capital                $  100,000.00
Final NAV                       $  684,456.28
Total Return                          584.46%
CAGR                                   13.69%
Sharpe Ratio                            0.648
Volatility (ann.)                      16.04%
Max Drawdown                          -38.68%
Cohorts Traded                            180
Win Rate                               78.89%
Avg Cohort Return                       7.02%
Realized P&L                    $  578,828.25
```

### Residual Momentum (126-21) - 6 Month Holdings - Top 20 - Russell 3000
```
Period               2010-01-04 to 2024-12-31
Starting Capital                $  100,000.00
Final NAV                       $  899,573.26
Total Return                          799.57%
CAGR                                   15.78%
Sharpe Ratio                            0.586
Volatility (ann.)                      23.30%
Max Drawdown                          -43.11%
Cohorts Traded                            180
Win Rate                               68.33%
Avg Cohort Return                       8.78%
Realized P&L                    $  809,069.28
```

### Residual Momentum (126-21) - 12 Month Holdings - Top 20 - Russell 3000
```
Period               2010-01-04 to 2024-12-31
Starting Capital                $  100,000.00
Final NAV                       $  644,182.08
Total Return                          544.18%
CAGR                                   13.23%
Sharpe Ratio                            0.500
Volatility (ann.)                      22.20%
Max Drawdown                          -40.24%
Cohorts Traded                            180
Win Rate                               70.56%
Avg Cohort Return                      15.28%
Realized P&L                    $  542,314.02
```

### Low Volatility (126) - 6 Month Holdings - Top 20 - Russell 3000 - Quality Filters of: Price > $5, Min 200M MC, Min $1M Avg. Volume - 21 Days
```
Period               2010-01-04 to 2024-12-31
Starting Capital                $  100,000.00
Final NAV                       $  330,218.31
Total Return                          230.22%
CAGR                                    8.30%
Sharpe Ratio                            0.474
Volatility (ann.)                       9.70%
Max Drawdown                          -31.65%
Cohorts Traded                            180
Win Rate                               78.89%
Avg Cohort Return                       4.17%
Realized P&L                    $  224,637.90
```

### Value - 6 Month Holdings - Top 20 - Russell 3000 - Quality Filters of: Price > $5, Min 200M MC, Min $1M Avg. Volume - 21 Days
```
Period               2010-01-04 to 2024-12-31
Starting Capital                $  100,000.00
Final NAV                       $  613,649.61
Total Return                          513.65%
CAGR                                   12.87%
Sharpe Ratio                            0.488
Volatility (ann.)                      22.37%
Max Drawdown                          -57.93%
Cohorts Traded                            180
Win Rate                               69.44%
Avg Cohort Return                       7.23%
Realized P&L                    $  499,965.40
```


## IC Results

### Residual Momentum 126-21
```
IC Summary — residual_momentum_126_21
============================================================
                Mean IC   ICIR  T-Stat  % Positive   Obs
Horizon (days)                                          
21               0.0438 0.3987  8.3551      0.7044  6393
63               0.0589 0.5640  7.1744      0.7515  6351
126              0.0747 0.7210  6.3731      0.8475  6288
252              0.0680 0.5439  3.8083      0.7967  6162

Guidelines: Mean IC > 0.05 | ICIR > 0.5 | |T-Stat| > 2.0
```

### Momentum 126-21
```
IC Summary — momentum_126_21
============================================================
                Mean IC   ICIR  T-Stat  % Positive   Obs
Horizon (days)                                          
21               0.0442 0.3829  8.2651      0.7064  6750
63               0.0613 0.5676  7.5159      0.7651  6708
126              0.0773 0.7011  6.5184      0.8426  6645
252              0.0708 0.5348  3.9250      0.8061  6519

Guidelines: Mean IC > 0.05 | ICIR > 0.5 | |T-Stat| > 2.0
```

### Value
```
IC Summary — value
============================================================
                Mean IC   ICIR  T-Stat  % Positive   Obs
Horizon (days)                                          
21               0.0720 0.7269 14.9971      0.8066  6876
63               0.1037 0.9335 11.1352      0.8728  6834
126              0.1289 1.0760  9.1182      0.8957  6771
252              0.1462 1.1637  7.0794      0.8840  6645

Guidelines: Mean IC > 0.05 | ICIR > 0.5 | |T-Stat| > 2.0
```

### Volatility (126)
```
IC Summary — volatility_126
============================================================
                Mean IC    ICIR   T-Stat  % Positive   Obs
Horizon (days)                                            
21              -0.0939 -0.5759 -11.8818      0.2517  6750
63              -0.1290 -0.7249  -8.7813      0.2097  6708
126             -0.1548 -0.8278  -6.9172      0.1812  6645
252             -0.1773 -0.9127  -5.7236      0.1724  6519

Guidelines: Mean IC > 0.05 | ICIR > 0.5 | |T-Stat| > 2.0
```

---

## Full Pipeline Architecture

### Pipeline Overview
```
Stage 1: Factor Screen
  Factor model scores Russell 3000 -> top 150-300 candidates
  Currently: momentum only (core idea is to use dual momentum)

Stage 2: REDACTED

Stage 3: REDACTED

Stage 4: Exit Rules
  - P(price > target) < 0.7 -> sell
  - Target reached early -> evaluate remaining Omega
  - 6-month max horizon -> close, roll capital
```

### Stage 2: REDACTED

**Factor-informed drift:**
- Composite factor z-score maps to annualized expected return
- Mapping via expanding-window regression (only completed cohort data)
- Example: z-score +2 -> risk-free + 12%, z-score +1 -> risk-free + 6%

**Models:** 
- REDACTED

**Selection:** 
- REDACTED

### Stage 3: REDACTED

- REDACTED

---

## Research Roadmap
```
**Phase 1 — Factor research** - COMPLETE
**Phase 1b — Universe quality filters** - COMPLETE
**Phase 2 — SCRAPPED**
**Phase 3 — **REDACTED** 
**Phase 4 — **Portfolio risk controls**
**Phase 5 — **REDACTED**
**Phase 6 — Options (ThetaData/ORATS/Massive) integration** WILL SKIP FOR NOW DUE TO COSTS
**Phase 7 — Forward test**
**Phase 8 — Paper trading (IBKR)**
```
---

## Key Papers

Phase 1: Jegadeesh & Titman (1993), Asness Moskowitz Pedersen (2013), Frazzini & Pedersen (2014)
Phase 3: Black & Scholes (1973), Merton (1976), Hoeting et al (1999) BMA
Phase 4: Daniel & Moskowitz (2016), Barroso & Santa-Clara (2015), Ledoit & Wolf (2004)
Phase 5: Merton (1976) jump diffusion
Phase 6: Xing Zhang Zhao (2010), Cremers & Weinbaum (2010), Pan & Poteshman (2006)
Phase 7: Harvey Liu Zhu (2016), McLean & Pontiff (2016), Lopez de Prado (2018)
Books: Grinold & Kahn, Lopez de Prado

---

## Conventions & Preferences

- Polars for data processing (not pandas unless necessary)
- Content-hash caching pattern throughout (spec_hash)
- Each module has one clear responsibility
- Tests in Tests/, pytest
- Research in Research/Notebooks/
- Specs are frozen dataclasses
- Paths centralized in Core/Config/paths.py
- REDACTED
- 1/N equal weighting within cohorts
- Git for version control — commit before changes
- ALWAYS verify universe parquet before running backtests
