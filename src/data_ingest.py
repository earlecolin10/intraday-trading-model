"""Data ingestion interfaces for loading and cleaning market datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_minute_bars(data_dir: Path, symbols: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    """Load minute bars for symbols over a date range."""
    raise NotImplementedError("Minute bar loading is not implemented in scaffold.")


def load_daily_bars(data_dir: Path, symbols: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    """Load daily bars for symbols over a date range."""
    raise NotImplementedError("Daily bar loading is not implemented in scaffold.")


def clean_minute_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Apply generic cleaning and normalization to minute bar data."""
    raise NotImplementedError("Minute bar cleaning is not implemented in scaffold.")


def build_universe_snapshot(daily_df: pd.DataFrame) -> list[str]:
    """Return symbols that pass base universe constraints."""
    raise NotImplementedError("Universe construction is not implemented in scaffold.")
