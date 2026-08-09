from dataclasses import dataclass
from typing import Mapping, Literal


@dataclass(frozen=True)
class CombineSpec:
    """
    Specifies how multiple normalized factor columns are combined
    into a single composite score for ranking.

    method:
        'none'   - pass through a single factor directly (no combination).
                   Requires exactly one factor in SignalSpec.
        'equal'  - equal-weight average across all factors.
                   No weights needed.
        'linear' - weighted sum. Requires weights to be provided.
                   Weights do not need to sum to 1 (they are applied as-is).

    weights:
        Mapping of canonical factor column name → weight.
        Required when method='linear', must be None otherwise.
        Keys must match factor column names derived from FactorSpec.
    """

    method: Literal['none', 'equal', 'linear', 'ridge']
    weights: Mapping[str, float] | None = None

    def __post_init__(self):
        if self.method == 'linear' and not self.weights:
            raise ValueError(
                "CombineSpec.method='linear' requires weights to be provided"
            )
        if self.method in ('none', 'equal') and self.weights is not None:
            raise ValueError(
                f"CombineSpec.method='{self.method}' does not use weights"
            )

    def identity(self) -> dict:
        base = {
            'method': self.method,
            'weights': (
                dict(sorted(self.weights.items()))
                if self.weights is not None
                else None
            ),
        }
        return base
