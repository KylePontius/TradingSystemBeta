from dataclasses import dataclass
from typing import Tuple
from .filter import FilterSpec


@dataclass(frozen=True)
class UniverseSpec:
    """
    Class that specifies how a universe should be defined.
    """
    name:    str
    base:    str
    filters: Tuple[FilterSpec, ...] | None = None

    def identity(self) -> dict:
        return {
            "base": self.base,
            "filters": (
                [
                    f.identity()
                    for f in sorted(self.filters, key=lambda f: str(f.identity()))
                ]
                if self.filters
                else []
            ),
        }