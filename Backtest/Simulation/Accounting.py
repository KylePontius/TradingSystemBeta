"""
Accounting.py
-------------
Computes how much capital to deploy into a new cohort portfolio
given the current master NAV, number of active cohorts, and the
CapitalAllocationSpec.
"""

from Core.Config.specs.capital import CapitalAllocationSpec

def computeCohortTarget(
    nav:            float,
    availableCash:  float,
    activeCohorts:  int,
    holdingPeriods: int,
    spec:           CapitalAllocationSpec,
) -> float:
    """
    Compute the capital to deploy into a new cohort.

    Parameters
    ----------
    nav : float
        Current master portfolio NAV (cash + all active cohort values).
    availableCash : float
        Uninvested cash currently sitting in the master portfolio.
    activeCohorts : int
        Number of cohort portfolios currently alive (before adding the new one).
    holdingPeriods : int
        Maximum number of simultaneously active cohorts (from StrategySpec).
    spec : CapitalAllocationSpec

    Returns
    -------
    float
        Dollar amount to invest in the new cohort. May be 0 if policy is
        'skip' and there is insufficient cash.
    """

    if spec.method == "equalSplit":
        # Target = NAV / total cohort slots
        # Example: hold 6 months, form monthly -> 6 slots -> each gets 1/6 of NAV
        target = nav / holdingPeriods

    else:
        raise ValueError(f"Unknown capitalAllocation.method: {spec.method!r}")

    # Apply shortfall policy 
    if availableCash >= target:
        return target

    # Cash is insufficient to fully fund the target
    if spec.shortfallPolicy == "investAvailable":
        return availableCash

    elif spec.shortfallPolicy == "skip":
        return 0.0

    elif spec.shortfallPolicy == "scaleExisting":
        # Not implemented in simulation loop yet —
        # requires reaching into live cohorts to claw back capital.
        # Return 0 for now so the caller can handle it explicitly.
        raise NotImplementedError(
            "shortfallPolicy='scaleExisting' is not yet implemented"
        )

    else:
        raise ValueError(f"Unknown shortfallPolicy: {spec.shortfallPolicy!r}")