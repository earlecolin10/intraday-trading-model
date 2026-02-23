"""Feature engineering interfaces for intraday and daily market features."""

from __future__ import annotations

import pandas as pd


def build_intraday_features(minute_df: pd.DataFrame, daily_df: pd.DataFrame) -> pd.DataFrame:
    """Construct feature matrix used by setup detectors and risk checks."""
    raise NotImplementedError("Intraday feature building is not implemented in scaffold.")


def compute_opening_range(minute_df: pd.DataFrame, minutes: int = 15) -> tuple[float, float]:
    """Compute opening range high/low for the given initial session window."""
    raise NotImplementedError("Opening range computation is not implemented in scaffold.")


def compute_vwap(minute_df: pd.DataFrame) -> pd.Series:
    """Compute session VWAP series."""
    raise NotImplementedError("VWAP computation is not implemented in scaffold.")


def compute_relative_volume(minute_df: pd.DataFrame, historical_profile: pd.DataFrame) -> pd.Series:
    """Compute intraday relative volume against historical time-of-day profile."""
    raise NotImplementedError("Relative volume computation is not implemented in scaffold.")
