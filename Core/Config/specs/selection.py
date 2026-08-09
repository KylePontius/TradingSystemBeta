from dataclasses import dataclass
from typing import Literal

SelectionMethod = Literal["topN", "bottomN", "topPct", "bottomPct"]

@dataclass(frozen=True)
class SelectionSpec:
    '''
    Selects what part of and how much of eligible universe is chosen for trading.
    ''' 
    method: SelectionMethod
    value: float

    def __post_init__(self):
        if "Pct" in self.method and not (0 < self.value <= 100):
            raise ValueError("Percent selection must be in (0, 100]")
        if "N" in self.method and self.value <= 0:
            raise ValueError("N selection must be positive")
    

    def identity(self) -> dict:
        return {
            'method' : self.method,
            'value' : self.value,
        }