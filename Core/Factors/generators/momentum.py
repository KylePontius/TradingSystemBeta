import polars as pl

def computeMomentum(
    prices: pl.LazyFrame,
    lookback: int,
    buffer: int,
    priceColumn: str = "closeadj",
) -> pl.LazyFrame:
    """
    Compute momentum (log-return) for all tickers.

    Momentum definition:
        log(P[t - buffer]) - log(P[t - lookback])

    Parameters
    ----------
    prices : pl.LazyFrame
        Must contain: date | ticker | priceColumn
        Expected to include all tickers and all dates.
    lookback : int
        Lookback window in trading days (e.g. 252)
    buffer : int
        Skip window to avoid short-term reversal (e.g. 21)
    priceColumn : str
        Price column to use (default: closeadj)

    Returns
    -------
    pl.LazyFrame
        date | ticker | value
    """

    if buffer >= lookback:
        raise ValueError("buffer must be < lookback")

    return (
        prices
        .select("date", "ticker", priceColumn)
        .sort(["ticker", "date"])
        .with_columns([
            pl.col(priceColumn)
              .log()
              .shift(buffer)
              .over("ticker")
              .alias("endPrice"),

            pl.col(priceColumn)
              .log()
              .shift(lookback)
              .over("ticker")
              .alias("startPrice"),
        ])
        .with_columns(
            (pl.col("endPrice") - pl.col("startPrice")).alias("value")
        )
        .select("date", "ticker", "value")
        .filter(pl.col("value").is_not_null())
    )
