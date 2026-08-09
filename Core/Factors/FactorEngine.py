from pathlib import Path
import polars as pl

from Core.Config.specs.factor import FactorSpec
from Core.Config.utils import spec_hash
from .generators.momentum import computeMomentum
from .generators.volatility import computeVolatility
from .generators.jtVolatility import computejtVolatility
from .generators.residualMomentum import computeResidualMomentum
from .generators.value import computeValue
from .generators.marketcap import computeMarketCap
from .generators.dollarVolume import computeDollarVolume
from .generators.price import computePrice
from Core.Config.paths import FACTORS_DIR
from Core.Config.paths import STOCK_DIR

FACTORS_DIR.mkdir(parents=True, exist_ok=True)

FACTOR_REGISTRY = {
    "momentum": {
        "func": computeMomentum,
        "requires": ("lookback", "buffer"),
    },
    "volatility": {
        "func": computeVolatility,
        "requires": ("window",),
    },
    "jt_volatility" : {
        "func" : computejtVolatility,
        "requires": ("lookback", "buffer")
    },
    "residual_momentum" : {
        "func" : computeResidualMomentum,
        "requires" : ("lookback", "buffer")
    },
    "value" : {
        "func" : computeValue,
        "requires" : ()
    },
    "marketcap" : {
        "func" : computeMarketCap,
        "requires" : ()
    },
    "dollar_volume" : {
        "func" : computeDollarVolume,
        "requires" : ("window",)
    },
    "price" : {
        "func" : computePrice,
        "requires" : ()
    }
}

def makeColumnName(spec : FactorSpec):
    factor = FACTOR_REGISTRY[spec.type]
    order = factor['requires']

    parts = [spec.type]
    parts.extend(str(spec.params[p]) for p in order)
    return "_".join(parts)

def ensure(
    spec : FactorSpec
) -> Path:
    """
    Ensure factor parquet exists.

    Parameters
    ----------
    spec : FactorSpec
        FactorSpec instance which has type, 
        mapping of parameters, and optionally, weight of factor

    Returns
    -------
    Path
        Path to factor parquet file
    """

    if spec.type not in FACTOR_REGISTRY:
        raise ValueError(f"Unknown factor '{spec.type}'")

    factor = FACTOR_REGISTRY[spec.type]
    func = factor["func"]
    required = factor["requires"]

    missing = [p for p in required if p not in spec.params]
    if missing:
        raise ValueError(
            f"factor '{spec.type}' requires parameters {missing}"
        )

    unexpected = set(spec.params) - set(required)
    if unexpected:
        raise ValueError(f"Unexpected parameters {unexpected}")
    
    column = makeColumnName(spec)
    h = spec_hash(spec)
    filename = f"{column}_{h}.parquet"
    out_path = FACTORS_DIR / spec.type / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        return out_path

    prices = (
        pl.scan_parquet(STOCK_DIR / "ticker=*/0.parquet")
        .sort(["ticker", "date"])
        )

    factor = func(prices, **spec.params)

    expectedColumns = {"date", "ticker", 'value'}
    missing = expectedColumns - set(factor.collect_schema().names())
    if missing:
        raise ValueError(
            f"Factor '{spec.type}' missing columns {missing}"
        )
    factor = factor.sort(["date", "ticker"])
    factor = factor.rename({"value": column})
    factor.sink_parquet(out_path)

    return out_path


