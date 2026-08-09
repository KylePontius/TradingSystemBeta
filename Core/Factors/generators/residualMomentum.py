import polars as pl
from Core.Config.paths import BENCHMARKS_DIR

BENCHMARK_BASE = BENCHMARKS_DIR

BENCHMARK_REGISTRY = {
    'spy' : 'spy.parquet',
    
}

def computeResidualMomentum(
    prices: pl.LazyFrame,
    lookback: int,
    buffer: int,
    priceColumn: str = "closeadj",
    benchmark : str = "spy"
) -> pl.LazyFrame:
    """
    
    """
    if buffer >= lookback:
        raise ValueError("buffer must be < lookback")
    
    if benchmark.lower() not in BENCHMARK_REGISTRY:
        raise ValueError(f"{benchmark} not found in registry, please pick one of {BENCHMARK_REGISTRY.keys()}.")

    stockReturns = (
        prices
        .select("date", "ticker", priceColumn)
        .sort(["ticker", "date"])
        .with_columns(
            pl.col(priceColumn)
              .log()
              .diff()
              .over("ticker")
              .alias("StockReturns")
        )
        .filter(pl.col("StockReturns").is_not_null())
    )

    marketReturns = (
        pl.scan_parquet(BENCHMARK_BASE / BENCHMARK_REGISTRY[benchmark])
        .select("date", "ticker", 'MarketReturns'))

    betas = findBetas(stockReturns, marketReturns, lookback, buffer)

    residuals = computeResidualReturns(stockReturns, marketReturns, betas)

    return findResidualMomentum(residuals, lookback, buffer)

def findBetas(
    stockReturns : pl.LazyFrame, 
    marketReturns : pl.LazyFrame, 
    lookback : int, 
    buffer : int
) -> pl.LazyFrame:
    
    window = lookback - buffer
    joined = (
        stockReturns
        .join(
            marketReturns.select(['date', 'MarketReturns']),
            on='date',
            how='inner'
        )
        .sort(["ticker", "date"])
        .with_columns(
            pl.col('StockReturns').shift(buffer).alias('r_i'),
            pl.col('MarketReturns').shift(buffer).alias('r_m')
        )
    )

    return (
        joined
        .with_columns(
            pl.rolling_cov('r_i', 'r_m', window_size=window)
            .over('ticker')
            .alias('cov'),

            pl.col("r_m")
            .rolling_var(window_size=window)
            .over("ticker")
            .alias("var")
        )
        .with_columns(
            (pl.col("cov") / pl.col("var")).alias("beta")
        )
        .select("date", "ticker", "beta")
        .filter(pl.col("beta").is_not_null())
    )

def computeResidualReturns(
    stockReturns : pl.LazyFrame,
    marketReturns : pl.LazyFrame,
    betas : pl.LazyFrame
) -> pl.LazyFrame:
    
    return (
        stockReturns
        .join(
            marketReturns,
            on='date',
            how='inner'
        )
        .join(
            betas,
            on=['date', 'ticker'],
            how='inner'
        )
        .with_columns(
            (pl.col('StockReturns') - pl.col('beta') * pl.col('MarketReturns')).alias('ResidualReturns')
        )
        .select('date', 'ticker', 'ResidualReturns')
    )

def findResidualMomentum(
    residuals : pl.LazyFrame,
    lookback : int,
    buffer : int
) -> pl.LazyFrame:
    
    window = lookback - buffer

    return (
        residuals
        .sort(["ticker", "date"])
        .with_columns(
            pl.col('ResidualReturns')
            .shift(buffer)
            .rolling_sum(window_size=window)
            .over('ticker')
            .alias('value')
        )
        .select("date", "ticker", "value")
        .filter(pl.col("value").is_not_null())
    )

