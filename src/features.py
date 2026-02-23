"""Vectorized feature engineering utilities for daily and intraday OHLCV data.

Assumptions
-----------
- Input dataframes are indexed by timestamp-like indices.
- Input columns include: ``open``, ``high``, ``low``, ``close``, ``volume``.
- Intraday functions operate on one or more complete sessions.

Design notes
------------
- All computations are vectorized via pandas operations (no Python loops).
- Calculations are leakage-safe: each timestamp uses only current/past data.
"""

from __future__ import annotations

import pandas as pd


_REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


def compute_daily_atr(daily_df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute Average True Range (ATR) on daily bars using Wilder smoothing.

    True Range (TR) for day ``t`` is:
    ``max(high_t - low_t, abs(high_t - close_{t-1}), abs(low_t - close_{t-1}))``.

    ATR uses an exponential moving average with ``alpha = 1 / period`` (Wilder's
    smoothing convention), producing a causal, no-lookahead volatility estimate.

    Parameters
    ----------
    daily_df:
        Daily OHLCV dataframe indexed by date/timestamp.
    period:
        ATR smoothing period (default 14).

    Returns
    -------
    pd.Series
        ATR series aligned to ``daily_df.index``.
    """
    _ensure_required_columns(daily_df)
    _ensure_positive_period(period)

    prev_close = daily_df["close"].shift(1)
    tr = pd.concat(
        [
            daily_df["high"] - daily_df["low"],
            (daily_df["high"] - prev_close).abs(),
            (daily_df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    atr.name = f"atr_{period}"
    return atr


def compute_intraday_vwap(minute_df: pd.DataFrame) -> pd.Series:
    """Compute intraday VWAP with session reset.

    VWAP at timestamp ``t`` within each session is:
    ``sum_{i<=t}(typical_price_i * volume_i) / sum_{i<=t}(volume_i)``,
    where ``typical_price = (high + low + close) / 3``.

    The cumulative sums reset at each session boundary, so no cross-session bleed.

    Parameters
    ----------
    minute_df:
        Intraday OHLCV dataframe indexed by timestamp.

    Returns
    -------
    pd.Series
        Session-reset VWAP series aligned to ``minute_df.index``.
    """
    _ensure_required_columns(minute_df)
    _ensure_datetime_index(minute_df)

    session = minute_df.index.normalize()
    typical_price = (minute_df["high"] + minute_df["low"] + minute_df["close"]) / 3.0

    pv_cum = (typical_price * minute_df["volume"]).groupby(session).cumsum()
    vol_cum = minute_df["volume"].groupby(session).cumsum()

    vwap = pv_cum.div(vol_cum.where(vol_cum != 0))
    vwap.name = "vwap"
    return vwap


def compute_opening_range(minute_df: pd.DataFrame, minutes: int = 15) -> tuple[float, float]:
    """Compute opening-range high/low for the first ``minutes`` of the first session.

    Opening range is computed from the first timestamp of the first session through
    ``start + minutes`` (inclusive of bars that fall within that interval).

    Parameters
    ----------
    minute_df:
        Intraday OHLCV dataframe indexed by timestamp.
    minutes:
        Opening-range window length in minutes.

    Returns
    -------
    tuple[float, float]
        ``(opening_range_high, opening_range_low)``.
    """
    _ensure_required_columns(minute_df)
    _ensure_datetime_index(minute_df)
    _ensure_positive_period(minutes)

    sorted_df = minute_df.sort_index()
    first_session = sorted_df.index.normalize().min()
    session_df = sorted_df[sorted_df.index.normalize() == first_session]

    if session_df.empty:
        raise ValueError("Opening range cannot be computed from empty session data.")

    start_ts = session_df.index.min()
    end_ts = start_ts + pd.Timedelta(minutes=minutes)
    opening_slice = session_df.loc[(session_df.index >= start_ts) & (session_df.index < end_ts)]

    if opening_slice.empty:
        raise ValueError("Opening range window has no bars.")

    return float(opening_slice["high"].max()), float(opening_slice["low"].min())


def compute_relative_volume(minute_df: pd.DataFrame, lookback_days: int = 20) -> pd.Series:
    """Compute leakage-safe relative volume (RVOL) from cumulative volume profiles.

    For each bar, RVOL is defined as:
    ``cum_volume_today_at_bar_k / mean(cum_volume_prior_sessions_at_bar_k)``
    where ``bar_k`` is minute offset from session open.

    The denominator uses only prior sessions via ``shift(1)`` before rolling mean,
    preventing future leakage.

    Parameters
    ----------
    minute_df:
        Intraday OHLCV dataframe indexed by timestamp.
    lookback_days:
        Number of prior sessions used for the rolling baseline.

    Returns
    -------
    pd.Series
        Relative volume series aligned to ``minute_df.index``.
    """
    _ensure_required_columns(minute_df)
    _ensure_datetime_index(minute_df)
    _ensure_positive_period(lookback_days)

    sorted_df = minute_df.sort_index()
    session = sorted_df.index.normalize()
    bar_number = sorted_df.groupby(session).cumcount()
    cum_volume = sorted_df["volume"].groupby(session).cumsum()

    baseline = cum_volume.groupby(bar_number).transform(
        lambda s: s.shift(1).rolling(window=lookback_days, min_periods=1).mean()
    )

    rvol = cum_volume.div(baseline.where(baseline > 0))
    rvol = rvol.replace([float("inf"), float("-inf")], pd.NA)
    rvol.name = f"rvol_{lookback_days}"
    return rvol


def compute_intraday_range(minute_df: pd.DataFrame) -> pd.Series:
    """Compute running intraday session range (high-water minus low-water).

    For each session and timestamp ``t``:
    ``range_t = cummax(high)_t - cummin(low)_t``.

    This is causal and does not use future bars.

    Parameters
    ----------
    minute_df:
        Intraday OHLCV dataframe indexed by timestamp.

    Returns
    -------
    pd.Series
        Running session range series aligned to ``minute_df.index``.
    """
    _ensure_required_columns(minute_df)
    _ensure_datetime_index(minute_df)

    session = minute_df.index.normalize()
    running_high = minute_df["high"].groupby(session).cummax()
    running_low = minute_df["low"].groupby(session).cummin()

    intraday_range = running_high - running_low
    intraday_range.name = "intraday_range"
    return intraday_range


def compute_ema(minute_df: pd.DataFrame, period: int = 9) -> pd.Series:
    """Compute causal EMA of intraday close prices.

    EMA is computed with pandas ``ewm(span=period, adjust=False)`` and therefore
    only uses current/past closes at each timestamp.

    Parameters
    ----------
    minute_df:
        Intraday OHLCV dataframe indexed by timestamp.
    period:
        EMA lookback period.

    Returns
    -------
    pd.Series
        EMA series aligned to ``minute_df.index``.
    """
    _ensure_required_columns(minute_df)
    _ensure_positive_period(period)

    ema = minute_df["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    ema.name = f"ema_{period}"
    return ema


def _ensure_required_columns(df: pd.DataFrame) -> None:
    """Validate required OHLCV columns are present."""
    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {missing}")


def _ensure_datetime_index(df: pd.DataFrame) -> None:
    """Validate that dataframe index is datetime-like."""
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        raise ValueError("DataFrame index must be datetime-like.")


def _ensure_positive_period(period: int) -> None:
    """Validate period/lookback inputs."""
    if period <= 0:
        raise ValueError("Period/lookback must be positive.")
