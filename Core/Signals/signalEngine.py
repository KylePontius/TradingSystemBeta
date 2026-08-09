from pathlib import Path
import polars as pl

from Core.Config.specs.factor import FactorSpec
from Core.Config.specs.signal import SignalSpec
from Core.Config.specs.selection import SelectionSpec
from Core.Config.specs.ranking import RankSpec
from Core.Config.utils import spec_hash
from Core.Factors.FactorEngine import ensure as ensureFactor
from Core.Universe.UniverseEngine import ensure as ensureUniverse
from Core.Factors.FactorEngine import makeColumnName

from Core.Config.paths import SIGNALS_DIR

SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

def ensure(spec: SignalSpec) -> Path:
    """
    Ensure that a signal parquet artifact exists for the given SignalSpec.
    If it already exists (content-hash match), return its path immediately.
    Otherwise compute and persist it.

    Returns
-
    Path
        Path to the signal parquet file.

    Naming rule:
        Signals/{signal_name}/{signal_name}_{hash}.parquet
    """

    # 1. Determine signal identity
    h = spec_hash(spec)

    out_dir = SIGNALS_DIR / spec.name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{spec.name}_{h}.parquet"

    if out_path.exists():
        return out_path

    # 2. Load universe
    universePath = ensureUniverse(spec.universe)

    df = (
        pl.scan_parquet(universePath)
        .select("date", "ticker")
    )

    # 3. Load and join factors
    for factor in spec.factors:
        factorPath = ensureFactor(factor)
        col = makeColumnName(factor)

        lf = (
            pl.scan_parquet(factorPath)
            .select("date", "ticker", pl.col(col))
        )

        df = df.join(lf, on=["date", "ticker"], how="inner")

    # 4. Normalize factors
    norm = spec.normalize

    for factor in spec.factors:
        col = makeColumnName(factor)
        x = pl.col(col)

        # log transform
        if norm.transform == "log":
            x = x.log()

        # winsorize
        if norm.winsorize is not None:
            lo, hi = norm.winsorize
            lower = x.quantile(lo).over("date")
            upper = x.quantile(hi).over("date")
            x = x.clip(lower, upper)

        # trim top (remove highest values)
        if norm.trimTopPct is not None:
            q = 1.0 - norm.trimTopPct / 100.0
            upper = x.quantile(q).over("date")
            df = df.filter(x <= upper)

        # trim bottom (remove lowest values)
        if norm.trimBtmPct is not None:
            q = norm.trimBtmPct / 100.0
            lower = x.quantile(q).over("date")
            df = df.filter(x >= lower)

        # cross-sectional normalization
        if norm.method == "zscore":
            mu = x.mean().over("date")
            sd = x.std(ddof=0).over("date")
            x = pl.when(sd == 0).then(0.0).otherwise((x - mu) / sd)

        elif norm.method == "rank":
            x = x.rank("dense").over("date")

        elif norm.method == "none":
            pass

        else:
            raise ValueError(f"Unknown normalize method: {norm.method!r}")
        
        # long/short
        x = x * factor.direction

        df = df.with_columns(x.alias(col))

    # 5. Combine factors -> composite score
    combine = spec.combined
    factorKeys = [makeColumnName(f) for f in spec.factors]

    if combine.method == "none":
        # Single factor pass-through
        scoreExpression = pl.col(factorKeys[0])
        df = df.with_columns(scoreExpression.alias("score"))

    elif combine.method == "equal":
        # Equal-weight average across all factors
        scoreExpression = sum(pl.col(k) for k in factorKeys) / len(factorKeys)
        df = df.with_columns(scoreExpression.alias("score"))

    elif combine.method == "linear":
        # Weighted sum - weights provided by user
        missing = set(combine.weights) - set(factorKeys)
        if missing:
            raise ValueError(f"Unknown factor keys in CombineSpec.weights: {missing}")
        scoreExpression = sum(
            combine.weights[k] * pl.col(k)
            for k in factorKeys
        )
        df = df.with_columns(scoreExpression.alias("score"))

    else:
        raise ValueError(f"Unknown combine method: {combine.method!r}")

    # 6. Rank cross-sectionally
    ranking = spec.ranking

    if ranking.method == "single":
        rank_col = pl.col(makeColumnName(ranking.source))
    elif ranking.method == "multi":
        rank_col = pl.col("score")
    else:
        raise ValueError(f"Unknown ranking method: {ranking.method!r}")

    descending = ranking.order == "desc"

    df = df.with_columns(
        rank_col
        .rank("dense", descending=descending)
        .over("date")
        .alias("rank")
    )

    # 7. Convert ranks -> signals
    n = pl.len().over("date")

    long = (
        _apply_selection(pl.col("rank"), n, spec.long)
        if spec.long is not None
        else pl.lit(False)
    )

    short = (
        _apply_selection(pl.col("rank"), n, spec.short)
        if spec.short is not None
        else pl.lit(False)
    )

    df = df.with_columns(
        pl.when(long).then(pl.lit(1))
          .when(short).then(pl.lit(-1))
          .otherwise(pl.lit(0))
          .alias("signal")
    )

    df = df.filter(pl.col("signal") != 0)

    # 8. Persist
    df.select("date", "ticker", "signal", "score", "rank").sink_parquet(out_path)

    return out_path


# Helpers

def _apply_selection(
    rank: pl.Expr,
    n: pl.Expr,
    spec: SelectionSpec,
) -> pl.Expr:

    if spec.method == "topN":
        return rank <= spec.value

    if spec.method == "bottomN":
        return rank > n - spec.value

    if spec.method == "topPct":
        return rank <= n * (spec.value / 100)

    if spec.method == "bottomPct":
        return rank > n * (1 - spec.value / 100)

    raise ValueError(f"Unknown selection method: {spec.method!r}")