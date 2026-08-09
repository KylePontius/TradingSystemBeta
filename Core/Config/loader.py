"""
loader.py
---------
Parses a YAML config file into a fully validated BacktestSpec.

Usage:
    from Core.Config.loader import load
    spec = load("Configs/example.yaml")
"""

import yaml
from datetime import date
from pathlib import Path

from .specs.run import RunSpec
from .specs.factor import FactorSpec
from .specs.filter import FilterSpec
from .specs.universe import UniverseSpec
from .specs.normalize import NormalizeSpec
from .specs.combine import CombineSpec
from .specs.ranking import RankSpec
from .specs.selection import SelectionSpec
from .specs.signal import SignalSpec
from .specs.capital import CapitalAllocationSpec
from .specs.position import PositionAllocationSpec
from .specs.strategy import StrategySpec
from .specs.backtest import BacktestSpec
from .specs.slippage import SlippageSpec

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load(path: str | Path) -> BacktestSpec:
    """
    Load a YAML config file and return a fully validated BacktestSpec.

    Parameters
    ----------
    path : str or Path
        Path to the YAML config file.

    Returns
    -------
    BacktestSpec

    Raises
    ------
    FileNotFoundError
        If the YAML file does not exist.
    KeyError / ValueError
        If required fields are missing or values are invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    return _parse_backtest(raw)


# ---------------------------------------------------------------------------
# Top-level parser
# ---------------------------------------------------------------------------

def _parse_backtest(raw: dict) -> BacktestSpec:
    _require(raw, ["run", "universe", "factors", "signals", "strategy"])

    # Build a named factor registry so signals can reference factors by name
    factor_registry = _parse_factor_registry(raw["factors"])

    return BacktestSpec(
        run=_parse_run(raw["run"]),
        strategy=_parse_strategy(raw["strategy"]),
        signal=_parse_signal(raw["signals"], raw["universe"], factor_registry),
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def _parse_run(raw: dict) -> RunSpec:
    _require(raw, ["name", "start", "end", "capital"], section="run")
    return RunSpec(
        name=str(raw["name"]),
        start=_parse_date(raw["start"], "run.start"),
        end=_parse_date(raw["end"], "run.end"),
        capital=float(raw["capital"]),
    )


# ---------------------------------------------------------------------------
# Factors
# ---------------------------------------------------------------------------

def _parse_factor_registry(raw: dict) -> dict[str, FactorSpec]:
    """
    Parse the top-level `factors:` block into a dict of name -> FactorSpec.

    Each entry looks like:
        momentum_252_21:
            type: momentum
            lookback: 252
            buffer: 21
            weight: 0.5   # optional
            direction: -1  # optional, default 1
    """
    registry = {}
    for name, cfg in raw.items():
        _require(cfg, ["type"], section=f"factors.{name}")
        factor_type = cfg["type"]
        weight = cfg.get("weight", None)
        direction = cfg.get("direction", 1)
        params = {k: v for k, v in cfg.items() if k not in ("type", "weight", "direction")}
        registry[name] = FactorSpec(type=factor_type, params=params, weight=weight, direction=direction)
    return registry


# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

def _parse_universe(raw: dict, factor_registry: dict[str, FactorSpec]) -> UniverseSpec:
    _require(raw, ["base"], section="universe")

    filters_raw = raw.get("filters", None)
    filters = None

    if filters_raw:
        filters = tuple(
            _parse_filter(name, cfg, factor_registry)
            for name, cfg in filters_raw.items()
        )

    return UniverseSpec(
        name=raw.get("name", raw["base"]),
        base=raw["base"],
        filters=filters,
    )


def _parse_filter(name: str, raw: dict, factor_registry: dict[str, FactorSpec]) -> FilterSpec:
    _require(raw, ["type", "op", "threshold"], section=f"universe.filters.{name}")

    factor_type = raw["type"]
    params = {k: v for k, v in raw.items() if k not in ("type", "op", "threshold")}
    factor = FactorSpec(type=factor_type, params=params)

    return FilterSpec(
        factor=factor,
        op=raw["op"],
        threshold=float(raw["threshold"]),
    )


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

def _parse_signal(raw: dict, universe_raw: dict, factor_registry: dict[str, FactorSpec]) -> SignalSpec:
    _require(raw, ["name", "normalize", "combine", "ranking"], section="signals")

    universe = _parse_universe(universe_raw, factor_registry)
    normalize = _parse_normalize(raw["normalize"])
    combine = _parse_combine(raw["combine"])
    ranking = _parse_ranking(raw["ranking"], factor_registry)

    long_spec = _parse_selection(raw["long"], "signals.long") if "long" in raw else None
    short_spec = _parse_selection(raw["short"], "signals.short") if "short" in raw else None

    return SignalSpec(
        name=str(raw["name"]),
        universe=universe,
        factors=tuple(factor_registry.values()),
        normalize=normalize,
        combined=combine,
        ranking=ranking,
        long=long_spec,
        short=short_spec,
    )


def _parse_normalize(raw: dict) -> NormalizeSpec:
    _require(raw, ["transform", "method"], section="signals.normalize")
    return NormalizeSpec(
        transform=raw["transform"],
        method=raw["method"],
        winsorize=tuple(raw["winsorize"]) if "winsorize" in raw else None,
        trimTopPct=raw.get("trimTopPct", None),
        trimBtmPct=raw.get("trimBtmPct", None),
    )


def _parse_combine(raw: dict) -> CombineSpec:
    _require(raw, ["method"], section="signals.combine")
    return CombineSpec(
        method=raw["method"],
        weights=raw.get("weights", None),
    )


def _parse_ranking(raw: dict, factor_registry: dict[str, FactorSpec]) -> RankSpec:
    _require(raw, ["method", "order"], section="signals.ranking")

    source = None
    if raw["method"] == "single":
        _require(raw, ["source"], section="signals.ranking")
        source_name = raw["source"]
        if source_name not in factor_registry:
            raise KeyError(
                f"signals.ranking.source '{source_name}' not found in factors block"
            )
        source = factor_registry[source_name]

    return RankSpec(
        method=raw["method"],
        order=raw["order"],
        source=source,
    )


def _parse_selection(raw: dict, section: str) -> SelectionSpec:
    _require(raw, ["method", "value"], section=section)
    return SelectionSpec(
        method=raw["method"],
        value=float(raw["value"]),
    )


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

def _parse_strategy(raw: dict) -> StrategySpec:
    _require(
        raw,
        ["formationFrequency", "timeBasis", "holdingPeriods",
         "holdingUnit", "capitalAllocation", "positionAllocation"],
        section="strategy",
    )

    slippage_raw = raw.get("slippage", {})
    slippage = SlippageSpec(
        model=slippage_raw.get("model", "spread"),
        sizeBased=slippage_raw.get("sizeBased", True),
        defaultSpread=slippage_raw.get("defaultSpread", 0.001),
    )

    return StrategySpec(
        formationFrequency=raw["formationFrequency"],
        timeBasis=raw["timeBasis"],
        holdingPeriods=int(raw["holdingPeriods"]),
        holdingUnit=raw["holdingUnit"],
        capitalAllocation=_parse_capital_allocation(raw["capitalAllocation"]),
        positionAllocation=_parse_position_allocation(raw["positionAllocation"]),
        slippage=slippage,
    )


def _parse_capital_allocation(raw: dict) -> CapitalAllocationSpec:
    _require(raw, ["basis", "method"], section="strategy.capitalAllocation")
    return CapitalAllocationSpec(
        basis=raw["basis"],
        method=raw["method"],
        shortfallPolicy=raw.get("shortfallPolicy", "investAvailable"),
    )


def _parse_position_allocation(raw: dict) -> PositionAllocationSpec:
    _require(raw, ["method"], section="strategy.positionAllocation")
    return PositionAllocationSpec(
        method=raw["method"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require(d: dict, keys: list[str], section: str = "config") -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise KeyError(
            f"Missing required field(s) in '{section}': {missing}"
        )


def _parse_date(value, field: str) -> date:
    """Accept a date object (yaml auto-parses) or an ISO string."""
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(
            f"'{field}' must be a valid ISO date (YYYY-MM-DD), got: {value!r}"
        )
    

if __name__ == "__main__":
    spec = load("Configs/example.yaml")
    print(spec.run)
    print(spec.strategy)
    print(spec.signal.name)


# """
# loader.py
# ---------
# Parses a YAML config file into a fully validated BacktestSpec.

# Usage:
#     from Core.Config.loader import load
#     spec = load("Configs/example.yaml")
# """

# import yaml
# from datetime import date
# from pathlib import Path

# from .specs.run import RunSpec
# from .specs.factor import FactorSpec
# from .specs.filter import FilterSpec
# from .specs.universe import UniverseSpec
# from .specs.normalize import NormalizeSpec
# from .specs.combine import CombineSpec
# from .specs.ranking import RankSpec
# from .specs.selection import SelectionSpec
# from .specs.signal import SignalSpec
# from .specs.capital import CapitalAllocationSpec
# from .specs.position import PositionAllocationSpec
# from .specs.strategy import StrategySpec
# from .specs.backtest import BacktestSpec
# from .specs.slippage import SlippageSpec

# # ---------------------------------------------------------------------------
# # Public API
# # ---------------------------------------------------------------------------

# def load(path: str | Path) -> BacktestSpec:
#     """
#     Load a YAML config file and return a fully validated BacktestSpec.

#     Parameters
#     ----------
#     path : str or Path
#         Path to the YAML config file.

#     Returns
#     -------
#     BacktestSpec

#     Raises
#     ------
#     FileNotFoundError
#         If the YAML file does not exist.
#     KeyError / ValueError
#         If required fields are missing or values are invalid.
#     """
#     path = Path(path)
#     if not path.exists():
#         raise FileNotFoundError(f"Config file not found: {path}")

#     with open(path, "r") as f:
#         raw = yaml.safe_load(f)

#     return _parse_backtest(raw)


# # ---------------------------------------------------------------------------
# # Top-level parser
# # ---------------------------------------------------------------------------

# def _parse_backtest(raw: dict) -> BacktestSpec:
#     _require(raw, ["run", "universe", "factors", "signals", "strategy"])

#     # Build a named factor registry so signals can reference factors by name
#     factor_registry = _parse_factor_registry(raw["factors"])

#     return BacktestSpec(
#         run=_parse_run(raw["run"]),
#         strategy=_parse_strategy(raw["strategy"]),
#         signal=_parse_signal(raw["signals"], raw["universe"], factor_registry),
#     )


# # ---------------------------------------------------------------------------
# # Run
# # ---------------------------------------------------------------------------

# def _parse_run(raw: dict) -> RunSpec:
#     _require(raw, ["name", "start", "end", "capital"], section="run")
#     return RunSpec(
#         name=str(raw["name"]),
#         start=_parse_date(raw["start"], "run.start"),
#         end=_parse_date(raw["end"], "run.end"),
#         capital=float(raw["capital"]),
#     )


# # ---------------------------------------------------------------------------
# # Factors
# # ---------------------------------------------------------------------------

# def _parse_factor_registry(raw: dict) -> dict[str, FactorSpec]:
#     """
#     Parse the top-level `factors:` block into a dict of name -> FactorSpec.

#     Each entry looks like:
#         momentum_252_21:
#             type: momentum
#             lookback: 252
#             buffer: 21
#             weight: 0.5   # optional
#     """
#     registry = {}
#     for name, cfg in raw.items():
#         _require(cfg, ["type"], section=f"factors.{name}")
#         factor_type = cfg["type"]
#         weight = cfg.get("weight", None)
#         params = {k: v for k, v in cfg.items() if k not in ("type", "weight")}
#         registry[name] = FactorSpec(type=factor_type, params=params, weight=weight)
#     return registry


# # ---------------------------------------------------------------------------
# # Universe
# # ---------------------------------------------------------------------------

# def _parse_universe(raw: dict, factor_registry: dict[str, FactorSpec]) -> UniverseSpec:
#     _require(raw, ["base"], section="universe")

#     filters_raw = raw.get("filters", None)
#     filters = None

#     if filters_raw:
#         filters = tuple(
#             _parse_filter(name, cfg, factor_registry)
#             for name, cfg in filters_raw.items()
#         )

#     return UniverseSpec(
#         name=raw.get("name", raw["base"]),
#         base=raw["base"],
#         filters=filters,
#     )


# def _parse_filter(name: str, raw: dict, factor_registry: dict[str, FactorSpec]) -> FilterSpec:
#     _require(raw, ["type", "op", "threshold"], section=f"universe.filters.{name}")

#     factor_type = raw["type"]
#     params = {k: v for k, v in raw.items() if k not in ("type", "op", "threshold")}
#     factor = FactorSpec(type=factor_type, params=params)

#     return FilterSpec(
#         factor=factor,
#         op=raw["op"],
#         threshold=float(raw["threshold"]),
#     )


# # ---------------------------------------------------------------------------
# # Signal
# # ---------------------------------------------------------------------------

# def _parse_signal(raw: dict, universe_raw: dict, factor_registry: dict[str, FactorSpec]) -> SignalSpec:
#     _require(raw, ["name", "normalize", "combine", "ranking"], section="signals")

#     universe = _parse_universe(universe_raw, factor_registry)
#     normalize = _parse_normalize(raw["normalize"])
#     combine = _parse_combine(raw["combine"])
#     ranking = _parse_ranking(raw["ranking"], factor_registry)

#     long_spec = _parse_selection(raw["long"], "signals.long") if "long" in raw else None
#     short_spec = _parse_selection(raw["short"], "signals.short") if "short" in raw else None

#     return SignalSpec(
#         name=str(raw["name"]),
#         universe=universe,
#         factors=tuple(factor_registry.values()),
#         normalize=normalize,
#         combined=combine,
#         ranking=ranking,
#         long=long_spec,
#         short=short_spec,
#     )


# def _parse_normalize(raw: dict) -> NormalizeSpec:
#     _require(raw, ["transform", "method"], section="signals.normalize")
#     return NormalizeSpec(
#         transform=raw["transform"],
#         method=raw["method"],
#         winsorize=tuple(raw["winsorize"]) if "winsorize" in raw else None,
#         trimTopPct=raw.get("trimTopPct", None),
#         trimBtmPct=raw.get("trimBtmPct", None),
#     )


# def _parse_combine(raw: dict) -> CombineSpec:
#     _require(raw, ["method"], section="signals.combine")
#     return CombineSpec(
#         method=raw["method"],
#         weights=raw.get("weights", None),
#     )


# def _parse_ranking(raw: dict, factor_registry: dict[str, FactorSpec]) -> RankSpec:
#     _require(raw, ["method", "order"], section="signals.ranking")

#     source = None
#     if raw["method"] == "single":
#         _require(raw, ["source"], section="signals.ranking")
#         source_name = raw["source"]
#         if source_name not in factor_registry:
#             raise KeyError(
#                 f"signals.ranking.source '{source_name}' not found in factors block"
#             )
#         source = factor_registry[source_name]

#     return RankSpec(
#         method=raw["method"],
#         order=raw["order"],
#         source=source,
#     )


# def _parse_selection(raw: dict, section: str) -> SelectionSpec:
#     _require(raw, ["method", "value"], section=section)
#     return SelectionSpec(
#         method=raw["method"],
#         value=float(raw["value"]),
#     )


# # ---------------------------------------------------------------------------
# # Strategy
# # ---------------------------------------------------------------------------

# def _parse_strategy(raw: dict) -> StrategySpec:
#     _require(
#         raw,
#         ["formationFrequency", "timeBasis", "holdingPeriods",
#          "holdingUnit", "capitalAllocation", "positionAllocation"],
#         section="strategy",
#     )

#     slippage_raw = raw.get("slippage", {})
#     slippage = SlippageSpec(
#         model=slippage_raw.get("model", "spread"),
#         sizeBased=slippage_raw.get("sizeBased", True),
#         defaultSpread=slippage_raw.get("defaultSpread", 0.001),
#     )

#     return StrategySpec(
#         formationFrequency=raw["formationFrequency"],
#         timeBasis=raw["timeBasis"],
#         holdingPeriods=int(raw["holdingPeriods"]),
#         holdingUnit=raw["holdingUnit"],
#         capitalAllocation=_parse_capital_allocation(raw["capitalAllocation"]),
#         positionAllocation=_parse_position_allocation(raw["positionAllocation"]),
#         slippage=slippage,
#     )


# def _parse_capital_allocation(raw: dict) -> CapitalAllocationSpec:
#     _require(raw, ["basis", "method"], section="strategy.capitalAllocation")
#     return CapitalAllocationSpec(
#         basis=raw["basis"],
#         method=raw["method"],
#         shortfallPolicy=raw.get("shortfallPolicy", "investAvailable"),
#     )


# def _parse_position_allocation(raw: dict) -> PositionAllocationSpec:
#     _require(raw, ["method"], section="strategy.positionAllocation")
#     return PositionAllocationSpec(
#         method=raw["method"],
#     )


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def _require(d: dict, keys: list[str], section: str = "config") -> None:
#     missing = [k for k in keys if k not in d]
#     if missing:
#         raise KeyError(
#             f"Missing required field(s) in '{section}': {missing}"
#         )


# def _parse_date(value, field: str) -> date:
#     """Accept a date object (yaml auto-parses) or an ISO string."""
#     if isinstance(value, date):
#         return value
#     try:
#         return date.fromisoformat(str(value))
#     except ValueError:
#         raise ValueError(
#             f"'{field}' must be a valid ISO date (YYYY-MM-DD), got: {value!r}"
#         )
    

# if __name__ == "__main__":
#     spec = load("Configs/example.yaml")
#     print(spec.run)
#     print(spec.strategy)
#     print(spec.signal.name)