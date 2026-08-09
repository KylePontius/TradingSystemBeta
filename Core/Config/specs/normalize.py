from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class NormalizeSpec:
    """
    Specifies how factor values are normalized cross-sectionally
    before ranking or combining.

    transform:
        Pre-normalization transformation applied to raw factor values.
        'none' | 'log'

    method:
        Cross-sectional normalization method.
        'none'   - no normalization
        'zscore' - subtract cross-sectional mean, divide by std
        'rank'   - replace values with cross-sectional dense rank

    winsorize:
        Optional (low, high) tuple of quantiles to clip values to
        before normalization. E.g. (0.01, 0.99) clips to 1st/99th pct.
        Must satisfy 0 < low < high < 1.

    trimTopPct:
        Drop the top X% of stocks by factor value from the universe
        before ranking. E.g. 1.0 removes the top 1%.

    trimBtmPct:
        Drop the bottom X% of stocks by factor value from the universe
        before ranking. E.g. 1.0 removes the bottom 1%.
    """

    transform:  Literal['none', 'log']
    method:     Literal['none', 'zscore', 'rank']
    winsorize:  tuple[float, float] | None = None
    trimTopPct: Optional[float] = None
    trimBtmPct: Optional[float] = None

    def __post_init__(self):
        if self.winsorize is not None:
            lo, hi = self.winsorize
            if not (0 < lo < hi < 1):
                raise ValueError(
                    "NormalizeSpec.winsorize must be (low, high) with 0 < low < high < 1"
                )
        if self.trimTopPct is not None and not (0 < self.trimTopPct < 100):
            raise ValueError("NormalizeSpec.trimTopPct must be in (0, 100)")
        if self.trimBtmPct is not None and not (0 < self.trimBtmPct < 100):
            raise ValueError("NormalizeSpec.trimBtmPct must be in (0, 100)")

    def identity(self) -> dict:
        return {
            'transform':  self.transform,
            'method':     self.method,
            'winsorize':  tuple(self.winsorize) if self.winsorize else None,
            'trimTopPct': self.trimTopPct,
            'trimBtmPct': self.trimBtmPct,
        }