import polars as pl
from Core.Config.paths import SHARADAR_DIR

def computeValue(
    prices: pl.LazyFrame,  # date | ticker (used for trading date spine)
) -> pl.LazyFrame:
    """
    Compute composite value factor for all tickers.
    
    Composite = equal-weight z-score of:
        - FCF yield:       fcf / marketcap
        - Earnings yield:  netinc / marketcap
        - Book-to-market:  equity / marketcap
    
    Point-in-time safe: uses datekey as the as-of date.
    
    Parameters
    ----------
    prices : pl.LazyFrame
        Must contain: date | ticker
        Used to build the trading date spine.
    
    Returns
    -------
    pl.LazyFrame
        date | ticker | value
    """

    # date x ticker combinations
    spine = (
        prices
        .select("date", "ticker")
        .unique()
        .sort(["ticker", "date"])
    )

    sf1 = pl.scan_csv(SHARADAR_DIR / "sharadarSF1.csv")

    # Filter SF1 to ARQ
    fundamentals = (
        sf1
        .filter(pl.col("dimension") == "ARQ")
        .select(["ticker", "datekey", "fcf", "netinc", "equity", "marketcap"])
        .with_columns(pl.col("datekey").cast(pl.Date))
        .filter(
            pl.col("marketcap").is_not_null() &
            (pl.col("marketcap") > 0)
        )
        .with_columns([
            (pl.col("fcf") / pl.col("marketcap")).alias("fcf_yield"),
            (pl.col("netinc") / pl.col("marketcap")).alias("earnings_yield"),
            (pl.col("equity") / pl.col("marketcap")).alias("book_to_market"),
        ])
        .select(["ticker", "datekey", "fcf_yield", "earnings_yield", "book_to_market"])
        .sort(["ticker", "datekey"])
    )

    # For each trading date, get most recent filing
    joined = (
        spine.collect()
        .join_asof(
            fundamentals.collect(),
            left_on="date",
            right_on="datekey",
            by="ticker",
            strategy="backward"
        )
        .lazy()
    )

    # Cross-sectional z-score each metric then equal-weight sum
    result = (
        joined
        .with_columns([
            ((pl.col("fcf_yield") - pl.col("fcf_yield").mean().over("date")) /
             pl.col("fcf_yield").std().over("date")).alias("z_fcf"),
            ((pl.col("earnings_yield") - pl.col("earnings_yield").mean().over("date")) /
             pl.col("earnings_yield").std().over("date")).alias("z_earnings"),
            ((pl.col("book_to_market") - pl.col("book_to_market").mean().over("date")) /
             pl.col("book_to_market").std().over("date")).alias("z_btm"),
        ])
        .with_columns(
            ((pl.col("z_fcf") + pl.col("z_earnings") + pl.col("z_btm")) / 3).alias("value")
        )
        .select("date", "ticker", "value")
        .filter(pl.col("value").is_not_null())
    )

    return result