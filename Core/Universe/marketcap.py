# import polars as pl
# from Core.Config.paths import STOCK_DIR, UNIVERSE_DIR, SHARADAR_DIR
# from Core.Universe.masterUniverse import masterUniverse

# def buildRussell3000() -> None:
#     tickers = masterUniverse().collect()

#     # Get marketcap from SF1 for time t
#     mc = (
#         pl.scan_csv(SHARADAR_DIR / "sharadarSF1.csv")
#         .filter(pl.col("dimension") == "ARQ")
#         .select(["ticker", "datekey", "marketcap"])
#         .with_columns(pl.col("datekey").str.to_date())
#         .filter(pl.col("marketcap").is_not_null() & (pl.col("marketcap") > 0))
#         .sort(["ticker", "datekey"])
#         .collect()
#     )

#     sep = (
#         pl.scan_parquet(STOCK_DIR / "ticker=*/0.parquet")
#         .select("date", "ticker")
#         .unique()
#         .collect()
#         .join(tickers, on="ticker", how="inner")
#         .sort(["ticker", "date"])
#     )

#     # for time t, marketcap on each trading date
#     sep_with_mc = (
#         sep
#         .join_asof(mc, left_on="date", right_on="datekey", by="ticker", strategy="backward")
#         .filter(pl.col("marketcap").is_not_null())
#     )

#     # Keep top 3000 by marketcap on each date
#     result = (
#         sep_with_mc
#         .sort(["date", "marketcap"], descending=[False, True])
#         .group_by("date", maintain_order=True)
#         .head(3000)
#         .select("date", "ticker")
#         .sort(["date", "ticker"])
#     )

#     out_path = UNIVERSE_DIR / "Russell3000.parquet"
#     result.write_parquet(out_path)
#     print(f"Built Russell3000: {result.shape}")
#     print(f"Dates: {result['date'].n_unique()}")
#     print(f"Tickers: {result['ticker'].n_unique()}")

import polars as pl
from datetime import datetime
from Core.DateProcessing.TradingDays import getTradingDays
from Core.Universe.masterUniverse import masterUniverse
def createUniverseByMarketCap(name : str, size : int):
    '''
    WORKS BUT IS INEFFICIENT, OPTIMIZE LATER.

    :type name: str
    :param size: Description
    :type size: int
    '''
    sf1 = (
    pl.scan_csv(r"C:/Users/Kyle/.vscode/projects/TradingSystem/Data/Sharadar/sharadarSF1.csv")
    .rename({'datekey' : 'date'})
    .with_columns([
        pl.col('date').cast(pl.Date),
    ])
    .select(['date', 'ticker', 'marketcap'])
    .with_columns(
            pl.col("marketcap").fill_null(-1)
    )
    .unique()
    .sort(['ticker', 'date'])
    .collect(engine='streaming')
    )
    universe = set(masterUniverse().collect(engine="streaming")["ticker"].to_list())

    days = getTradingDays(datetime(1995, 1, 1), datetime(2025, 5, 30))
    days = [d.date() for d in days]
    tickers = pl.DataFrame({'ticker' : list(universe)})
    joined = (
        pl.DataFrame({"date": days}).join(
            tickers, how='cross'
        )
        .with_columns([
            pl.col('date').cast(pl.Date)
        ])
        .sort(['ticker', 'date'])
    )
    result = []
    for ticker in set(sf1['ticker']):
        if ticker not in universe:
            continue
        tempdf = sf1.filter(pl.col("ticker") == ticker)

        resultComponent = joined.filter(pl.col("ticker") == ticker)
        resultComponent = (
            resultComponent.join(
                tempdf.select(["ticker", "date", "marketcap"]),
                on=["ticker", "date"],
                how="left"
            )
            .with_columns(
                pl.col("marketcap").forward_fill().fill_null(-1)
            )
        )
        result.append(resultComponent)
    result = pl.concat(result)
    result = (
        result
        .filter(pl.col("marketcap") != -1)
        .sort(by=["date", "marketcap"], descending = [False, True])
        .group_by("date", maintain_order=True)
        .head(size)
    )
    result.write_parquet(rf"C:/Users/Kyle/.vscode/projects/TradingSystem/Data/Universe/{name}.parquet")
    return result

