from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SlippageSpec:
    """
    Specifies the slippage model applied on position entry and exit.

    model:
        'spread'  — bid-ask spread as a fraction of price, applied as
                    half-spread per side (entry pays more, exit receives less).

    sizeBased:
        If True, spread varies by market cap tier:
            Large cap  (> $10B):          5bps per side
            Mid cap    ($2B - $10B):      10bps per side
            Small cap  ($300M - $2B):     20bps per side
            Micro cap  (< $300M):         40bps per side
        If False, defaultSpread is used for all stocks.

    defaultSpread:
        Half-spread fraction applied when sizeBased=False, or when
        market cap data is unavailable for a ticker.
        Default: 0.001 (10bps = 0.1%).
    """

    model: Literal['spread', 'none'] = 'spread'
    sizeBased: bool = True
    defaultSpread: float = 0.001  # 10bps

    def __post_init__(self):
        if not (0 <= self.defaultSpread <= 0.1):
            raise ValueError("SlippageSpec.defaultSpread must be in [0, 0.1]")

    def getSpread(self, marketCap: float | None) -> float:
        """
        Return the half-spread fraction for a given market cap.

        Parameters
        ----------
        marketCap : float or None
            Market cap in dollars. If None, returns defaultSpread.

        Returns
        -------
        float
            Half-spread as a fraction of price (e.g. 0.0005 = 5bps).
        """
        if self.model == 'none':
            return 0.0

        if not self.sizeBased or marketCap is None:
            return self.defaultSpread

        if marketCap >= 10_000_000_000:    # > $10B — large cap
            return 0.0005                  # 5bps
        elif marketCap >= 2_000_000_000:   # $2B-$10B — mid cap
            return 0.0010                  # 10bps
        elif marketCap >= 300_000_000:     # $300M-$2B — small cap
            return 0.0020                  # 20bps
        else:                              # < $300M — micro cap
            return 0.0040                  # 40bps

    def adjustEntry(self, price: float, marketCap: float | None, direction: str) -> float:
        """
        Adjust entry price for slippage.
        Long:  pay more  (price * (1 + spread))
        Short: receive less (price * (1 - spread))
        """
        spread = self.getSpread(marketCap)
        if direction == 'long':
            return price * (1 + spread)
        else:
            return price * (1 - spread)

    def adjustExit(self, price: float, marketCap: float | None, direction: str) -> float:
        """
        Adjust exit price for slippage.
        Long:  receive less (price * (1 - spread))
        Short: pay more    (price * (1 + spread))
        """
        spread = self.getSpread(marketCap)
        if direction == 'long':
            return price * (1 - spread)
        else:
            return price * (1 + spread)

    def identity(self) -> dict:
        return {
            'model':         self.model,
            'sizeBased':     self.sizeBased,
            'defaultSpread': self.defaultSpread,
        }