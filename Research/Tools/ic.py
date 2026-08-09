"""
ic.py--
Information Coefficient (IC) analysis for factor research.

IC measures the cross-sectional correlation between a factor's ranks
on date t and forward returns over the next N trading days.

Usage:
    from Research.Tools.ic import ICAnalysis
    from Core.Config.specs.factor import FactorSpec

    spec = FactorSpec(type="momentum", params={"lookback": 252, "buffer": 21})
    ic = ICAnalysis(spec, holdingDays=[21, 63, 126, 252])
    ic.compute()
    ic.summary()
    ic.plot()
"""

import polars as pl
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path
from scipy import stats
import statsmodels.api as sm

from Core.Config.specs.factor import FactorSpec
from Core.Factors.FactorEngine import ensure as ensureFactor, makeColumnName
from Core.Config.paths import STOCK_DIR


class ICAnalysis:
    """
    Computes and analyzes the Information Coefficient for a given factor.

    Parameters
-
    spec : FactorSpec
        The factor to analyze.
    holdingDays : list of int
        Forward return horizons in trading days to compute IC for.
        Default: [21, 63, 126, 252] (1, 3, 6, 12 months approx.)
    method : str
        'rank' for Spearman rank IC (recommended, robust to outliers)
        'pearson' for Pearson IC
    universeFilter : callable, optional
        Optional function to filter the factor DataFrame before computing IC.
        Receives a Polars DataFrame, returns a filtered Polars DataFrame.
    """

    def __init__(
        self,
        spec:           FactorSpec,
        holdingDays:    list[int] = None,
        method:         str = 'rank',
        universeFilter  = None,
    ):
        self.spec          = spec
        self.holdingDays   = holdingDays or [21, 63, 126, 252]
        self.method        = method
        self.universeFilter = universeFilter
        self.factorCol     = makeColumnName(spec)
        self._results: dict[int, pd.Series] = {}

    # Compute

    def compute(self) -> "ICAnalysis":
        """
        Compute IC time series for all holding day horizons.
        Results stored in self._results as {horizon: pd.Series of IC values}.
        """
        print(f"Ensuring factor: {self.factorCol}")
        factorPath = ensureFactor(self.spec)

        print("Loading factor data...")
        factor = pl.read_parquet(factorPath)

        print("Loading price data for forward returns...")
        prices = (
            pl.scan_parquet(STOCK_DIR / "ticker=*/0.parquet")
            .select(["date", "ticker", "closeadj"])
            .sort(["ticker", "date"])
            .collect()
        )

        if self.universeFilter is not None:
            factor = self.universeFilter(factor)

        for horizon in self.holdingDays:
            print(f"Computing IC for {horizon}-day horizon...")
            self._results[horizon] = self._computeHorizon(factor, prices, horizon)

        print("Done.")
        return self

    def _computeHorizon(
        self,
        factor: pl.DataFrame,
        prices: pl.DataFrame,
        horizon: int,
    ) -> pd.Series:
        """
        Compute IC time series for a single forward return horizon.
        """

        # Compute forward returns
        fwdReturns = (
            prices
            .sort(["ticker", "date"])
            .with_columns([
                pl.col("closeadj")
                  .shift(-horizon)
                  .over("ticker")
                  .alias("futurePrice")
            ])
            .with_columns([
                ((pl.col("futurePrice") - pl.col("closeadj")) / pl.col("closeadj"))
                .alias("fwdReturn")
            ])
            .select(["date", "ticker", "fwdReturn"])
            .filter(pl.col("fwdReturn").is_not_null())
        )

        # Join factor with forward returns
        joined = (
            factor
            .join(fwdReturns, on=["date", "ticker"], how="inner")
            .filter(pl.col(self.factorCol).is_not_null())
            .filter(pl.col("fwdReturn").is_not_null())
        )

        # Compute cross-sectional IC per date
        dates = joined["date"].unique().sort()
        ic_values = {}

        for date in dates:
            day = joined.filter(pl.col("date") == date)

            if len(day) < 10:
                continue

            factor_vals = day[self.factorCol].to_numpy()
            return_vals = day["fwdReturn"].to_numpy()

            if self.method == 'rank':
                ic, _ = stats.spearmanr(factor_vals, return_vals)
            else:
                ic, _ = stats.pearsonr(factor_vals, return_vals)

            if not np.isnan(ic):
                ic_values[date] = ic

        series = pd.Series(ic_values)
        series.index = pd.to_datetime(series.index)
        series = series.sort_index()
        series.name = f"IC_{horizon}d"
        return series

    # Results access
    def icSeries(self, horizon: int) -> pd.Series:
        """Return the IC time series for a given horizon."""
        self._checkComputed()
        if horizon not in self._results:
            raise ValueError(f"Horizon {horizon} not in computed results: {list(self._results.keys())}")
        return self._results[horizon]

    def meanIC(self) -> pd.Series:
        """Mean IC across all dates for each horizon."""
        self._checkComputed()
        return pd.Series(
            {h: s.mean() for h, s in self._results.items()},
            name="Mean IC"
        )

    def icir(self) -> pd.Series:
        """
        Information Coefficient Information Ratio (ICIR).
        ICIR = mean(IC) / std(IC)
        Target > 0.5 for a useful factor.
        """
        self._checkComputed()
        return pd.Series(
            {h: s.mean() / s.std() if s.std() != 0 else 0.0
             for h, s in self._results.items()},
            name="ICIR"
        )

    def tStat(self) -> pd.Series:
        self._checkComputed()
        results = {}
        for h, s in self._results.items():
            n = len(s)
            if n > 0 and s.std() != 0:
                # Newey-West with lag = horizon due compensate for overlapping periods
                model = sm.OLS(s.values, np.ones(n))
                fit   = model.fit(cov_type='HAC', cov_kwds={'maxlags': h})
                results[h] = float(fit.tvalues[0])
            else:
                results[h] = 0.0
        return pd.Series(results, name="T-Stat (NW)")

    def pctPositive(self) -> pd.Series:
        """Fraction of dates with positive IC."""
        self._checkComputed()
        return pd.Series(
            {h: (s > 0).mean() for h, s in self._results.items()},
            name="% Positive"
        )

    # Summary
    def summary(self) -> pd.DataFrame:
        """Print a summary table of IC metrics across all horizons."""
        self._checkComputed()

        df = pd.DataFrame({
            "Mean IC":    self.meanIC(),
            "ICIR":       self.icir(),
            "T-Stat":     self.tStat(),
            "% Positive": self.pctPositive(),
            "Obs":        pd.Series({h: len(s) for h, s in self._results.items()}),
        })
        df.index.name = "Horizon (days)"

        print(f"\nIC Summary — {self.factorCol}")
        print("=" * 60)
        print(df.to_string(
            float_format=lambda x: f"{x:.4f}" if isinstance(x, float) else str(x)
        ))
        print("\nGuidelines: Mean IC > 0.05 | ICIR > 0.5 | |T-Stat| > 2.0")
        return df

    # Plotting - AI Generated
    def plot(self, horizon: int = None, figsize: tuple = (14, 10)):
        """
        Plot IC time series, cumulative IC, and IC distribution.

        Parameters
    -
        horizon : int, optional
            If provided, plot only this horizon. Otherwise plots all.
        figsize : tuple
        """
        self._checkComputed()

        horizons = [horizon] if horizon else self.holdingDays
        n = len(horizons)

        fig, axes = plt.subplots(3, n, figsize=figsize)
        if n == 1:
            axes = axes.reshape(3, 1)

        fig.suptitle(f"IC Analysis — {self.factorCol}", fontsize=13, fontweight="bold")

        colors = plt.cm.tab10.colors

        for i, h in enumerate(horizons):
            ic = self._results[h]
            color = colors[i % len(colors)]
            meanIC = ic.mean()
            icir_val = ic.mean() / ic.std() if ic.std() != 0 else 0

            ax1 = axes[0, i]
            ax1.bar(ic.index, ic.values, color=color, alpha=0.4, width=20)
            ax1.axhline(0, color='black', linewidth=0.8)
            ax1.axhline(meanIC, color=color, linewidth=1.5, linestyle='--',
                       label=f"Mean: {meanIC:.4f}")
            ax1.set_title(f"{h}-day horizon")
            ax1.set_ylabel("IC")
            ax1.legend(fontsize=8)
            ax1.grid(True, alpha=0.3)

            ax2 = axes[1, i]
            cumIC = ic.cumsum()
            ax2.plot(cumIC.index, cumIC.values, color=color, linewidth=1.5)
            ax2.axhline(0, color='black', linewidth=0.8)
            ax2.set_ylabel("Cumulative IC")
            ax2.set_xlabel("Date")
            ax2.grid(True, alpha=0.3)
            ax2.fill_between(cumIC.index, cumIC.values, 0,
                            where=cumIC.values >= 0, alpha=0.15, color=color)
            ax2.fill_between(cumIC.index, cumIC.values, 0,
                            where=cumIC.values < 0, alpha=0.15, color='red')

            ax3 = axes[2, i]
            ax3.hist(ic.values, bins=40, color=color, alpha=0.6, edgecolor='white')
            ax3.axvline(0, color='black', linewidth=0.8)
            ax3.axvline(meanIC, color=color, linewidth=1.5, linestyle='--')
            ax3.set_ylabel("Frequency")
            ax3.set_xlabel("IC")
            ax3.set_title(f"ICIR: {icir_val:.3f}")
            ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()
        return fig

    def _checkComputed(self):
        if not self._results:
            raise RuntimeError("No results found. Call compute() first.")