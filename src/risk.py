"""Risk management interfaces for sizing and portfolio-level constraints."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionPlan:
    """Position sizing output for a single trade candidate."""

    symbol: str
    quantity: int
    entry_price: float
    stop_price: float
    risk_dollars: float


@dataclass(frozen=True)
class RiskLimits:
    """Runtime risk limits used by the planner."""

    max_open_positions: int
    max_daily_loss_dollars: float
    max_total_risk_dollars: float


def position_size(entry: float, stop: float, equity: float, risk_fraction: float) -> int:
    """Calculate risk-based position size in shares."""
    raise NotImplementedError("Position sizing is not implemented in scaffold.")


def enforce_portfolio_limits(candidates: list[PositionPlan], limits: RiskLimits) -> list[PositionPlan]:
    """Filter or adjust candidate positions to satisfy portfolio constraints."""
    raise NotImplementedError("Portfolio limit enforcement is not implemented in scaffold.")


def daily_loss_limit_hit(realized_pnl: float, limit_dollars: float) -> bool:
    """Check whether daily loss limit has been breached."""
    raise NotImplementedError("Daily loss limit check is not implemented in scaffold.")
