from dataclasses import dataclass
from .factor import FactorSpec

@dataclass(frozen=True)
class FilterSpec:
    '''
    Defines how the base universe should be filtered/reduced.
    '''
    factor: FactorSpec
    op: str          # "<=", ">=", "<", ">"
    threshold: float
    
    def identity(self) -> dict:
        return {
            'factor' : self.factor.identity(),
            'op' : self.op,
            'threshold' : self.threshold
        }