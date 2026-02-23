"""Market and symbol regime detection interfaces."""

from __future__ import annotations

import pandas as pd


def detect_market_regime(index_df: pd.DataFrame) -> pd.Series:
    """Classify broad market state (e.g., trend/chop) over time."""
    raise NotImplementedError("Market regime detection is not implemented in scaffold.")


def detect_symbol_regime(symbol_df: pd.DataFrame, market_regime: pd.Series) -> pd.Series:
    """Classify symbol-specific state conditioned on market context."""
    raise NotImplementedError("Symbol regime detection is not implemented in scaffold.")


def regime_is_tradeable(regime_value: str) -> bool:
    """Return whether a detected regime allows new entries."""
    raise NotImplementedError("Regime tradeability check is not implemented in scaffold.")
