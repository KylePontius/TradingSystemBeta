from dataclasses import dataclass
from typing import Mapping, Any, Literal

@dataclass(frozen=True)
class FactorSpec:
    '''Class that specifies how a factor should be defined.'''
    type: str
    params: Mapping[str, Any]
    weight: float | None = None
    direction: Literal[1, -1] = 1

    def identity(self) -> dict:
        return {
            "type": self.type,
            "params": dict(sorted(self.params.items())),
            "weight": self.weight,
            "direction" : self.direction
        }