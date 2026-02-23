"""Trade planning interfaces for producing executable intraday trade plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class TradePlan:
    """Executable trade plan scaffold for one symbol/setup."""

    ticker: str
    setup_name: str
    side: Literal["LONG", "SHORT"]
    entry_price: float
    stop_price: float
    target_price: float
    quantity: int
    confidence_score: float


def detect_setup_candidates(feature_df: pd.DataFrame) -> pd.DataFrame:
    """Return candidate rows that pass setup preconditions."""
    raise NotImplementedError("Setup detection is not implemented in scaffold.")


def build_trade_plan(candidate_row: pd.Series, account_equity: float) -> TradePlan:
    """Construct a trade plan object from one setup candidate."""
    raise NotImplementedError("Trade plan building is not implemented in scaffold.")


def generate_trade_plans(feature_map: dict[str, pd.DataFrame], account_equity: float) -> list[TradePlan]:
    """Generate ranked trade plans for the current decision snapshot."""
    raise NotImplementedError("Trade plan generation is not implemented in scaffold.")
