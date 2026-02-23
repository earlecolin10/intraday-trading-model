"""Application entrypoint scaffold for intraday trading model pipeline."""

from __future__ import annotations

from pathlib import Path

from config import load_config


def run_pipeline(config_path: Path | None = None) -> None:
    """Run end-to-end pipeline skeleton without executing live trading."""
    config = load_config(config_path)

    # 1) Load and clean input data (daily + intraday minute bars).
    # 2) Build leakage-safe features as-of each decision timestamp.
    # 3) Detect market/symbol regimes and setup candidates.
    # 4) Convert candidates into executable trade plans (entry/stop/target).
    # 5) Apply risk constraints and do-not-trade filters.
    # 6) Score and rank plans based on out-of-sample evidence.
    # 7) (Offline) run backtest/walk-forward evaluation and generate reports.
    # 8) Export candidate plans to JSON/CSV for manual review or paper trading.

    _ = config
    raise NotImplementedError("Pipeline orchestration is not implemented in scaffold.")


if __name__ == "__main__":
    # This scaffold does not place orders or run live trading.
    # Intended usage is architecture validation and iterative implementation.
    run_pipeline()
