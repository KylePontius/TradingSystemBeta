"""
results.py
----------
Analysis layer for a completed backtest.

Usage:
    from Backtest.Simulation.Simulate import run
    from Research.tools.results import Results

    master = run("Configs/example.yaml")
    results = Results(master)

    print(results.summary())
    results.plot()
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from Backtest.Portfolio.MasterPortfolio import MasterPortfolio


class Results:
    """
    Wraps a completed MasterPortfolio and provides analysis methods.

    Parameters
    ----------
    master : MasterPortfolio
        A fully simulated master portfolio returned by Simulate.run().
    riskFreeRate : float
        Annualised risk-free rate for Sharpe calculation. Default 0.04 (4%).
    """

    def __init__(self, master: MasterPortfolio, riskFreeRate: float = 0.04):
        self.master = master
        self.riskFreeRate = riskFreeRate
        self._nav = self._buildNav()

    # ------------------------------------------------------------------
    # Core data
    # ------------------------------------------------------------------

    def _buildNav(self) -> pd.Series:
        """Build a sorted NAV Series from master navHistory."""
        nav = pd.Series(self.master.navHistory)
        nav.index = pd.to_datetime(nav.index)
        nav = nav.sort_index()
        nav.name = self.master.name
        return nav

    def nav(self) -> pd.Series:
        """Return the full NAV time series."""
        return self._nav

    def returns(self, freq: str = "ME") -> pd.Series:
        """
        Compute period returns from the NAV series.

        Parameters
        ----------
        freq : str
            Resampling frequency. 'ME' = monthly, 'A' = annual, 'D' = daily.

        Returns
        -------
        pd.Series of period returns as decimals.
        """
        resampled = self._nav.resample(freq).last()
        return resampled.pct_change().dropna()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def cagr(self) -> float:
        """
        Compound Annual Growth Rate over the full backtest period.
        """
        start = self._nav.iloc[0]
        end   = self._nav.iloc[-1]
        years = (self._nav.index[-1] - self._nav.index[0]).days / 365.25
        return (end / start) ** (1 / years) - 1

    def sharpe(self) -> float:
        """
        Annualised Sharpe ratio using monthly returns.
        """
        monthlyRf = (1 + self.riskFreeRate) ** (1 / 12) - 1
        r = self.returns("ME")
        excess = r - monthlyRf
        if excess.std() == 0:
            return 0.0
        return float((excess.mean() / excess.std()) * np.sqrt(12))

    def volatility(self) -> float:
        """Annualised volatility using monthly returns."""
        return float(self.returns("ME").std() * np.sqrt(12))

    def maxDrawdown(self) -> float:
        """
        Maximum peak-to-trough drawdown over the full period.
        Returns a negative float, e.g. -0.35 means -35%.
        """
        rolling_max = self._nav.cummax()
        drawdown = (self._nav - rolling_max) / rolling_max
        return float(drawdown.min())

    def drawdownSeries(self) -> pd.Series:
        """Return the full drawdown time series."""
        rolling_max = self._nav.cummax()
        return (self._nav - rolling_max) / rolling_max

    def totalReturn(self) -> float:
        """Total return over the full backtest period."""
        return float(self._nav.iloc[-1] / self._nav.iloc[0] - 1)

    def winRate(self) -> float:
        """
        Fraction of closed cohort portfolios that had positive realized P&L.
        """
        if not self.master.tradingHistory:
            return 0.0
        wins = sum(1 for p in self.master.tradingHistory if p.realizedPnl > 0)
        return wins / len(self.master.tradingHistory)

    def avgCohortReturn(self) -> float:
        """
        Average return across all closed cohort portfolios.
        Return = realizedPnl / startBalance
        """
        if not self.master.tradingHistory:
            return 0.0
        returns = [
            p.realizedPnl / p.startBalance
            for p in self.master.tradingHistory
            if p.startBalance > 0
        ]
        return float(np.mean(returns)) if returns else 0.0

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> pd.Series:
        """
        Print a summary of key backtest metrics.
        """
        start = self._nav.index[0].date()
        end   = self._nav.index[-1].date()

        metrics = {
            "Period":             f"{start} to {end}",
            "Starting Capital":   f"${self.master.startBalance:>12,.2f}",
            "Final NAV":          f"${self._nav.iloc[-1]:>12,.2f}",
            "Total Return":       f"{self.totalReturn() * 100:.2f}%",
            "CAGR":               f"{self.cagr() * 100:.2f}%",
            "Sharpe Ratio":       f"{self.sharpe():.3f}",
            "Volatility (ann.)":  f"{self.volatility() * 100:.2f}%",
            "Max Drawdown":       f"{self.maxDrawdown() * 100:.2f}%",
            "Cohorts Traded":     len(self.master.tradingHistory),
            "Win Rate":           f"{self.winRate() * 100:.2f}%",
            "Avg Cohort Return":  f"{self.avgCohortReturn() * 100:.2f}%",
            "Realized P&L":       f"${self.master.realizedPnl:>12,.2f}",
        }

        s = pd.Series(metrics, name=self.master.name)
        print(s.to_string())
        return s

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot(self, benchmark: pd.Series = None, figsize: tuple = (14, 8)):
        """
        Plot the equity curve and drawdown.

        Parameters
        ----------
        benchmark : pd.Series, optional
            A NAV series to plot alongside (e.g. SPY). Must have a DatetimeIndex.
        figsize : tuple
            Figure size.
        """
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=figsize,
            gridspec_kw={"height_ratios": [3, 1]},
            sharex=True,
        )
        fig.suptitle(f"{self.master.name} — Backtest Results", fontsize=14, fontweight="bold")

        # --- Equity curve ---
        nav_indexed = self._nav / self._nav.iloc[0] * 100
        ax1.plot(nav_indexed.index, nav_indexed.values, label=self.master.name, linewidth=1.5, color="steelblue")

        if benchmark is not None:
            bench_indexed = benchmark / benchmark.iloc[0] * 100
            ax1.plot(bench_indexed.index, bench_indexed.values, label=benchmark.name or "Benchmark",
                     linewidth=1.5, color="gray", linestyle="--", alpha=0.8)

        ax1.set_ylabel("Growth of $100")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(mtick.FormatStrFormatter("$%.0f"))

        # Annotate final value
        ax1.annotate(
            f"${nav_indexed.iloc[-1]:.0f}",
            xy=(nav_indexed.index[-1], nav_indexed.iloc[-1]),
            xytext=(10, 0),
            textcoords="offset points",
            fontsize=9,
            color="steelblue",
        )

        # --- Drawdown ---
        dd = self.drawdownSeries() * 100
        ax2.fill_between(dd.index, dd.values, 0, color="red", alpha=0.4, label="Drawdown")
        ax2.plot(dd.index, dd.values, color="red", linewidth=0.8)
        ax2.set_ylabel("Drawdown (%)")
        ax2.set_xlabel("Date")
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))

        # Annotate max drawdown
        minIdx = dd.idxmin()
        ax2.annotate(
            f"{dd.min():.1f}%",
            xy=(minIdx, dd.min()),
            xytext=(10, -15),
            textcoords="offset points",
            fontsize=9,
            color="darkred",
        )

        plt.tight_layout()
        plt.show()
        return fig