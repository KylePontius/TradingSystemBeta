from pathlib import Path
import polars as pl

from Core.Config.specs.universe import UniverseSpec
from Core.Config.specs.filter import FilterSpec
from Core.Config.utils import spec_hash
from Core.Factors.FactorEngine import ensure as ensureFactor
from Core.Factors.FactorEngine import makeColumnName
from Core.Config.paths import UNIVERSE_DIR

UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)

def ensure(spec: UniverseSpec) -> Path:
    h = spec_hash(spec)
    out_path = UNIVERSE_DIR / f"{spec.base}_{h}.parquet"

    if out_path.exists():
        return out_path

    # 1. Load base universe
    basePath = UNIVERSE_DIR / f"{spec.base}.parquet"
    df = pl.scan_parquet(basePath).select("date", "ticker")

    # 2. Apply filters
    if spec.filters:
        for filterSpec in spec.filters:
            df = _applyFilter(df, filterSpec)

    # 3. Persist
    df.sink_parquet(out_path)
    return out_path

def _applyFilter(
    df: pl.LazyFrame,
    spec: FilterSpec,
) -> pl.LazyFrame:

    factor_path = ensureFactor(spec.factor)

    col = makeColumnName(spec.factor)

    factor = (
        pl.scan_parquet(factor_path)
        .select("date", "ticker", pl.col(col))
    )

    df = df.join(factor, on=["date", "ticker"], how="inner")

    if spec.op == ">=":
        df = df.filter(pl.col(col) >= spec.threshold)
    elif spec.op == "<=":
        df = df.filter(pl.col(col) <= spec.threshold)
    elif spec.op == ">":
        df = df.filter(pl.col(col) > spec.threshold)
    elif spec.op == "<":
        df = df.filter(pl.col(col) < spec.threshold)
    elif spec.op == "pct>=":
        df = df.with_columns(
            (
                pl.col(col).rank(method="ordinal").over("date") /
                pl.col(col).count().over("date")
            ).alias("__pct__")
        )
        df = df.filter(pl.col("__pct__") >= spec.threshold)
        df = df.drop(["__pct__", col])
        return df
    else:
        raise ValueError(f"Unknown filter op: {spec.op}")
    return df.drop(col)