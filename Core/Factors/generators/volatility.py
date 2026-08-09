import polars as pl

def computeVolatility(
    prices: pl.LazyFrame,
    window,
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

    if not isinstance(window, int):
        raise TypeError('Window must be an integer.')

    if window <= 0:
        raise ValueError('Window must be a positive integer.')
    

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

    return (
        returns
        .with_columns(
            pl.col("ret")
              .rolling_std(window_size=window)
              .over("ticker")
              .mul(252 ** 0.5)
              .alias("value")
        )
        .select("date", "ticker", "value")
        .filter(pl.col("value").is_not_null())
    )
