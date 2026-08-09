import polars as pl

def computejtVolatility(
    prices: pl.LazyFrame,
    lookback: int,
    buffer: int,
    priceColumn: str = "closeadj",
) -> pl.LazyFrame:
    """
    JT-style volatility:
        std( log returns from t-lookback+1 to t-buffer )
    """

    if buffer >= lookback:
        raise ValueError("buffer must be < lookback")

    returns = (
        prices
        .select("date", "ticker", priceColumn)
        .sort(["ticker", "date"])
        .with_columns(
            pl.col(priceColumn)
              .log()
              .diff()
              .over("ticker")
              .alias("ret")
        )
    )

    window = lookback - buffer

    return (
        returns
        .with_columns(
            pl.col("ret")
              .shift(buffer)
              .rolling_std(window_size=window)
              .over("ticker")
              .mul(252 ** 0.5)
              .alias("value")
        )
        .select("date", "ticker", "value")
        .filter(pl.col("value").is_not_null())
    )
