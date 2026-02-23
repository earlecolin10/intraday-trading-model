"""Scoring and ranking interfaces for trade candidate prioritization."""

from __future__ import annotations

from typing import Any


def compute_confidence_score(setup_name: str, context_key: str, oos_stats: dict[str, Any]) -> float:
    """Compute bounded confidence score (0-100) for a trade candidate."""
    raise NotImplementedError("Confidence scoring is not implemented in scaffold.")


def rank_candidates(candidate_scores: dict[str, float]) -> list[tuple[str, float]]:
    """Rank candidate identifiers from highest to lowest score."""
    raise NotImplementedError("Candidate ranking is not implemented in scaffold.")


def score_explanation_components(setup_name: str, oos_stats: dict[str, Any]) -> dict[str, float]:
    """Return explainability components used in confidence scoring."""
    raise NotImplementedError("Score explanation is not implemented in scaffold.")
