
"""Historical market data ingestion and validation utilities.

This module provides a production-oriented, file-based ingestion class for
loading daily and intraday OHLCV data from CSV files under a configured
`data_dir`.

No live/API pulling is implemented.
"""

"""Data ingestion interfaces for loading and cleaning market datasets."""


from __future__ import annotations

from pathlib import Path

import pandas as pd



class DataIngest:
    """Load, clean, and validate symbol OHLCV data from local CSV files.

    File layout expected under ``data_dir``:
    - ``minute/{symbol}.csv``
    - ``daily/{symbol}.csv``

    Required columns in source CSV:
    - Intraday: ``timestamp, open, high, low, close, volume``
    - Daily: ``date, open, high, low, close, volume``
    """

    _PRICE_COLUMNS = ["open", "high", "low", "close"]
    _NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume"]

    def __init__(self, data_dir: Path) -> None:
        """Initialize the ingestion service.

        Parameters
        ----------
        data_dir:
            Root data directory containing ``minute/`` and ``daily/`` folders.
        """
        self.data_dir = Path(data_dir)

    def load_minute(self, symbol: str) -> pd.DataFrame:
        """Load, clean, and validate intraday bars for one symbol.

        Parameters
        ----------
        symbol:
            Ticker symbol used to resolve ``data/minute/{symbol}.csv``.

        Returns
        -------
        pd.DataFrame
            Clean intraday dataframe indexed by timezone-aware timestamp.
        """
        filepath = self.data_dir / "minute" / f"{symbol}.csv"
        raw = self._read_csv(filepath)
        cleaned = self.clean(raw, intraday=True)
        self.validate(cleaned, intraday=True)
        return cleaned

    def load_daily(self, symbol: str) -> pd.DataFrame:
        """Load, clean, and validate daily bars for one symbol.

        Parameters
        ----------
        symbol:
            Ticker symbol used to resolve ``data/daily/{symbol}.csv``.

        Returns
        -------
        pd.DataFrame
            Clean daily dataframe indexed by date-like timestamp.
        """
        filepath = self.data_dir / "daily" / f"{symbol}.csv"
        raw = self._read_csv(filepath)
        cleaned = self.clean(raw, intraday=False)
        self.validate(cleaned, intraday=False)
        return cleaned

    def clean(self, df: pd.DataFrame, intraday: bool) -> pd.DataFrame:
        """Clean OHLCV data with deterministic, testable transformations.

        Cleaning rules implemented:
        - Parse and normalize timestamp/date column.
        - Sort index ascending and remove duplicate timestamps.
        - Convert OHLCV fields to numeric types.
        - Drop rows with missing OHLC values.
        - Ensure no negative prices.
        - Ensure volume is non-negative.

        Parameters
        ----------
        df:
            Raw dataframe loaded from CSV.
        intraday:
            Whether dataset is intraday (True) or daily (False).

        Returns
        -------
        pd.DataFrame
            Cleaned dataframe indexed by ``timestamp`` or ``date``.
        """
        time_col = "timestamp" if intraday else "date"
        self._ensure_required_columns(df, time_col)

        cleaned = df.copy()
        cleaned[time_col] = pd.to_datetime(cleaned[time_col], errors="coerce", utc=intraday)

        for col in self._NUMERIC_COLUMNS:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

        # Drop rows with invalid timestamp/date values.
        cleaned = cleaned.dropna(subset=[time_col])

        # Drop rows with missing OHLC values per requirement.
        cleaned = cleaned.dropna(subset=self._PRICE_COLUMNS)

        # Volume can be missing in raw sources; fill with 0 then validate non-negative.
        cleaned["volume"] = cleaned["volume"].fillna(0)

        # Remove invalid price/volume rows.
        cleaned = cleaned[(cleaned[self._PRICE_COLUMNS] >= 0).all(axis=1)]
        cleaned = cleaned[cleaned["volume"] >= 0]

        cleaned = cleaned.sort_values(time_col, ascending=True, kind="mergesort")
        cleaned = cleaned.drop_duplicates(subset=[time_col], keep="last")
        cleaned = cleaned.set_index(time_col)

        return cleaned

    def validate(self, df: pd.DataFrame, intraday: bool) -> None:
        """Validate cleaned OHLCV data and raise ``ValueError`` on failures.

        Validation rules implemented:
        - Index must be strictly increasing.
        - No duplicate index timestamps.
        - No negative or zero close prices.
        - Intraday data index must be timezone-aware.

        Parameters
        ----------
        df:
            Cleaned dataframe to validate.
        intraday:
            Whether dataset is intraday (True) or daily (False).

        Raises
        ------
        ValueError
            If any validation rule is violated.
        """
        if df.empty:
            raise ValueError("Validation failed: dataframe is empty after cleaning.")

        if not df.index.is_monotonic_increasing:
            raise ValueError("Validation failed: index must be strictly increasing.")

        if df.index.duplicated().any():
            raise ValueError("Validation failed: duplicate timestamps/dates found in index.")

        if (df["close"] <= 0).any():
            raise ValueError("Validation failed: close prices must be strictly positive.")

        if intraday and getattr(df.index, "tz", None) is None:
            raise ValueError("Validation failed: intraday index must be timezone-aware.")

    def _read_csv(self, filepath: Path) -> pd.DataFrame:
        """Read CSV file and raise helpful errors on missing/invalid files."""
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        try:
            df = pd.read_csv(filepath)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise ValueError(f"Failed to read CSV '{filepath}': {exc}") from exc

        if df.empty:
            raise ValueError(f"Data file is empty: {filepath}")

        return df

    def _ensure_required_columns(self, df: pd.DataFrame, time_col: str) -> None:
        """Ensure required schema exists before cleaning."""
        required = [time_col, *self._NUMERIC_COLUMNS]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

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

