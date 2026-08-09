from dataclasses import dataclass
from typing import Literal
from .factor import FactorSpec


@dataclass(frozen=True)
class RankSpec:
    """
    Specifies how stocks are ranked cross-sectionally to produce a signal.

    method:
        'single' — rank by a single factor directly.
                   Requires source to be provided.
        'multi'  — rank by the composite score produced by CombineSpec.
                   source must be None.

    order:
        'asc'  — ascending rank (lowest value = rank 1)
        'desc' — descending rank (highest value = rank 1)

    source:
        The FactorSpec to rank by when method='single'.
        Must be one of the factors already defined in SignalSpec.
    """

    method: Literal['single', 'multi']
    order:  Literal['asc', 'desc']
    source: FactorSpec | None = None

    def __post_init__(self):
        if self.method == 'single' and self.source is None:
            raise ValueError("RankSpec.method='single' requires source")
        if self.method == 'multi' and self.source is not None:
            raise ValueError("RankSpec.method='multi' must not define source")

    def identity(self) -> dict:
        from Core.Factors.FactorEngine import makeColumnName
        return {
            'method': self.method,
            'order':  self.order,
            'source': (
                makeColumnName(self.source)
                if self.source is not None
                else None
            ),
        }