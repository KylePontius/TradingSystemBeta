import polars as pl
from Core.Config.paths import SHARADAR_DIR

def computeMarketCap(
    prices: pl.LazyFrame,
) -> pl.LazyFrame:
    """
    Computes point-in-time market cap using Sharadar SF1 marketcap column,
    forward-filled to daily frequency via join_asof on datekey.

    Parameters
    ----------
    prices : pl.LazyFrame
        Must contain: date | ticker

    Returns
    -------
    pl.LazyFrame
        date | ticker | value
    """
    spine = (
        prices
        .select("date", "ticker")
        .unique()
        .sort(["ticker", "date"])
    )

    fundamentals = (
        pl.scan_csv(SHARADAR_DIR / "sharadarSF1.csv")
        .filter(pl.col("dimension") == "ARQ")
        .select(["ticker", "datekey", "marketcap"])
        .with_columns(pl.col("datekey").str.to_date())
        .filter(pl.col("marketcap").is_not_null() & (pl.col("marketcap") > 0))
        .sort(["ticker", "datekey"])
    )

    return (
        spine.collect()
        .join_asof(
            fundamentals.collect(),
            left_on="date",
            right_on="datekey",
            by="ticker",
            strategy="backward"
        )
        .lazy()
        .rename({"marketcap": "value"})
        .select("date", "ticker", "value")
        .filter(pl.col("value").is_not_null())
    )