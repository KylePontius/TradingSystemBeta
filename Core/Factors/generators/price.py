import polars as pl

def computePrice(
    prices: pl.LazyFrame,
) -> pl.LazyFrame:
    """
    Returns daily closing price for each ticker.
    Used as a filter factor (e.g. price >= 5 to exclude penny stocks).

    Parameters
    ----------
    prices : pl.LazyFrame
        Must contain: date | ticker | closeadj

    Returns
    -------
    pl.LazyFrame
        date | ticker | value
    """
    return (
        prices
        .select("date", "ticker", pl.col("closeadj").alias("value"))
        .filter(pl.col("value").is_not_null())
    )