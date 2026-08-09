import polars as pl
from Core.Config.paths import SHARADAR_DIR

def masterUniverse() -> pl.LazyFrame:
    tickers = pl.scan_csv(SHARADAR_DIR / "sharadarTickers.csv")
    eligible = (
        tickers
        .filter(
            (pl.col("exchange").is_in(["NYSE", "NASDAQ", "NYSEMKT", "AMEX"])) &
            (pl.col("category") == "Domestic Common Stock")
        )
        .select("ticker")
        .unique()
    )
    sf1_tickers = (
        pl.scan_csv(SHARADAR_DIR / "sharadarSF1.csv")
        .select("ticker")
        .unique()
    )
    sep_tickers = (
        pl.scan_csv(SHARADAR_DIR / "sharadarSEP.csv")
        .select("ticker")
        .unique()
    )
    return (
        eligible
        .join(sf1_tickers, on="ticker", how="inner")
        .join(sep_tickers, on="ticker", how="inner")
    )