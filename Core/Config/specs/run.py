from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class RunSpec:
    '''
    Class that defines basis of backtest, such as the name of it, 
    what day it begins, what day it ends, and how much to invest in it.
    '''
    name: str
    start: date
    end: date
    capital: float

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError("RunSpec.start must be before end")
        if self.capital <= 0:
            raise ValueError("RunSpec.capital must be positive")
        
