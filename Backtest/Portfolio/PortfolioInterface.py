from abc import ABC, abstractmethod
from datetime import datetime

class PortfolioInterface(ABC):

    @abstractmethod
    def value(self, date : datetime) -> float:
        '''
        A getter for Portfolio-type object's value (markedNav) at a given time.
        '''
        pass

    @abstractmethod
    def markToMarket(self, date : datetime):
        '''
        A function that updates a Portfolio-type 
        object's values for a given time, sets NAV for that date.
        '''
        pass