from dataclasses import dataclass


@dataclass(frozen=True)
class ForwardReturnSpec:
    """Specifies how forward returns should be computed."""

    holdingPeriodDays: int  # trading days (e.g. 126 ≈ 6 months)
    priceColumn: str = "closeadj"

    def identity(self) -> dict:
        return {
            "holdingPeriodDays": self.holdingPeriodDays,
            "priceColumn": self.priceColumn,
        }
