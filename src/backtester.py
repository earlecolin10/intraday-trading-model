"""Backtesting interfaces for leakage-safe intraday strategy evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class WalkForwardWindow:
    """Single walk-forward split definition."""

    train_start: str
    train_end: str
    test_start: str
    test_end: str


def generate_walkforward_windows(start: str, end: str, train_months: int = 6, test_months: int = 1) -> list[WalkForwardWindow]:
    """Create rolling train/test windows for time-series validation."""
    raise NotImplementedError("Walk-forward split generation is not implemented in scaffold.")


def run_backtest(trade_plans: pd.DataFrame, market_data: dict[str, pd.DataFrame], cost_config: dict[str, Any]) -> pd.DataFrame:
    """Simulate fills and returns for generated trade plans."""
    raise NotImplementedError("Backtest execution is not implemented in scaffold.")


def compute_backtest_metrics(trade_log: pd.DataFrame) -> dict[str, float]:
    """Compute aggregate performance and risk metrics from trade log."""
    raise NotImplementedError("Backtest metrics are not implemented in scaffold.")
