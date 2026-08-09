from pathlib import Path
import polars as pl

from Core.Config.specs.forwardReturn import ForwardReturnSpec
from Core.Config.utils import spec_hash
from Core.Config.paths import FACTORS_DIR, STOCK_DIR

FORWARD_RETURNS_DIR = FACTORS_DIR / "forward_returns"
FORWARD_RETURNS_DIR.mkdir(parents=True, exist_ok=True)


def ensure(spec: ForwardReturnSpec) -> Path:
    """
    Ensure forward return parquet exists.

    Computes the realized return over the next {holdingPeriodDays{
    trading days for every (date, ticker) pair. For stocks that delist
    mid-period, the last available price is used (partial return).

    Parameters
    ----------
    spec : ForwardReturnSpec
        Specifies holding period and price column.

    Returns
    -------
    Path
        Path to cached parquet with columns: date | ticker | forward_return
    """

    h = spec_hash(spec)
    filename = f"fwd_{spec.holdingPeriodDays}d_{h}.parquet"
    out_path = FORWARD_RETURNS_DIR / filename

    if out_path.exists():
        return out_path

    prices = (
        pl.scan_parquet(STOCK_DIR / "ticker=*/0.parquet")
        .select("date", "ticker", spec.priceColumn)
        .sort(["ticker", "date"])
    )

    forward_returns = _compute_forward_returns(prices, spec)
    forward_returns.sink_parquet(out_path)

    return out_path


def _compute_forward_returns(
    prices: pl.LazyFrame,
    spec: ForwardReturnSpec,
) -> pl.LazyFrame:
    """
    Compute forward returns for every (date, ticker) pair.

    For each row, the forward return is:
        P[t + actual_horizon] / P[t] - 1

    where actual_horizon = min(holdingPeriodDays, last available date for ticker).
    This handles delistings by using the last available price.

    Parameters
    ----------
    prices : pl.LazyFrame
        Must contain: date | ticker | priceColumn
    spec : ForwardReturnSpec
        Holding period and price column config.

    Returns
    -------
    pl.LazyFrame
        date | ticker | forward_return
    """

    col = spec.priceColumn
    period = spec.holdingPeriodDays

    # For each row, get the price {period} days ahead within the same ticker.
    # shift(-period) looks forward by {period} rows.
    # This naturally gives null if the stock has fewer than {period} rows remaining.
    result = (
        prices
        .with_columns(
            pl.col(col)
            .shift(-period)
            .over("ticker")
            .alias("future_price")
        )
    )

    # For rows where future_price is null (stock delisted or near end of data),
    # use the last available price for that ticker.
    result = (
        result
        .with_columns(
            pl.col(col)
            .last()
            .over("ticker")
            .alias("last_price")
        )
        .with_columns(
            pl.col("future_price")
            .fill_null(pl.col("last_price"))
            .alias("future_price")
        )
    )

    # Compute simple return. Filter out rows where entry price is null or zero,
    # and rows where the "forward" price is just the current price
    result = (
        result
        .with_columns(
            (pl.col("future_price") / pl.col(col) - 1.0).alias("forward_return")
        )
        .filter(
            pl.col(col).is_not_null()
            & (pl.col(col) > 0)
            & pl.col("forward_return").is_not_null()
        )
        .select("date", "ticker", "forward_return")
    )

    return result
