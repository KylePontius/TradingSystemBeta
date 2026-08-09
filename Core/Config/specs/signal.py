from dataclasses import dataclass
from typing import Tuple
from .universe import UniverseSpec
from .factor import FactorSpec
from .normalize import NormalizeSpec
from .combine import CombineSpec
from .ranking import RankSpec
from .selection import SelectionSpec


@dataclass(frozen=True)
class SignalSpec:
    """
    Fully specifies how a trading signal is constructed from factors.

    Pipeline:
        1. Restrict to universe (UniverseSpec)
        2. Load factor values (FactorSpec x N)
        3. Normalize each factor cross-sectionally (NormalizeSpec)
        4. Combine factors into a composite score (CombineSpec)
        5. Rank cross-sectionally (RankSpec)
        6. Select long / short candidates (SelectionSpec)

    name:
        Identifier used for caching the signal parquet artifact.

    long / short:
        At least one must be provided.
    """

    name:      str
    universe:  UniverseSpec
    factors:   Tuple[FactorSpec, ...]
    normalize: NormalizeSpec
    combined:  CombineSpec
    ranking:   RankSpec
    long:      SelectionSpec | None = None
    short:     SelectionSpec | None = None

    def __post_init__(self):
        if self.long is None and self.short is None:
            raise ValueError("SignalSpec must define at least one of long or short")

        keys = [self._column_name(f) for f in self.factors]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate factor column names in SignalSpec: {keys}")

        if self.combined.method == 'none' and len(self.factors) != 1:
            raise ValueError(
                "CombineSpec.method='none' requires exactly one factor in SignalSpec"
            )

        if self.ranking.method == 'single' and self.ranking.source is not None:
            source_key = self._column_name(self.ranking.source)
            if source_key not in keys:
                raise ValueError(
                    f"RankSpec.source '{source_key}' is not present in SignalSpec factors"
                )

    def _column_name(self, spec: FactorSpec) -> str:
        from Core.Factors.FactorEngine import makeColumnName
        return makeColumnName(spec)

    def identity(self) -> dict:
        return {
            'universe':  self.universe.identity(),
            'factors': {
                self._column_name(f): f.identity()
                for f in sorted(self.factors, key=self._column_name)
            },
            'normalize': self.normalize.identity(),
            'combined':  self.combined.identity(),
            'ranking':   self.ranking.identity(),
            'long':      self.long.identity() if self.long else None,
            'short':     self.short.identity() if self.short else None,
        }