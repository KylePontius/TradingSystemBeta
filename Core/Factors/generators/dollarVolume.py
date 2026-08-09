import polars as pl

def computeDollarVolume(
    prices: pl.LazyFrame,
    window: int = 21,
) -> pl.LazyFrame:
    """
    Computes rolling average daily dollar volume over a lookback window.
    Used as a liquidity filter factor.

    Dollar volume = closeadj * volume, averaged over window trading days.

    Parameters
    ----------
    prices : pl.LazyFrame
        Must contain: date | ticker | closeadj | volume
    window : int
        Rolling window in trading days (default: 21, ~1 month)

    Returns
    -------
    pl.LazyFrame
        date | ticker | value
    """
    return (
        prices
        .select("date", "ticker", "closeadj", "volume")
        .sort(["ticker", "date"])
        .with_columns(
            (pl.col("closeadj") * pl.col("volume")).alias("dv")
        )
        .with_columns(
            pl.col("dv")
            .rolling_mean(window_size=window)
            .over("ticker")
            .alias("value")
        )
        .select("date", "ticker", "value")
        .filter(pl.col("value").is_not_null())
    )