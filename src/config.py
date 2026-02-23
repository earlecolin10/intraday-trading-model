"""Configuration models and loaders for the intraday trading model scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RiskConfig:
    """Risk-related configuration values."""

    risk_per_trade: float
    max_open_positions: int
    max_daily_loss: float


@dataclass(frozen=True)
class DataConfig:
    """Data-related configuration values."""

    minute_data_path: Path
    daily_data_path: Path
    universe_min_price: float
    universe_min_dollar_volume: float


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration container."""

    data: DataConfig
    risk: RiskConfig
    timezone: str


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load and return application configuration from file/environment."""
    raise NotImplementedError("Configuration loading is not implemented in scaffold.")


def config_to_dict(config: AppConfig) -> dict[str, Any]:
    """Serialize config object into plain dictionary format."""
    raise NotImplementedError("Config serialization is not implemented in scaffold.")
