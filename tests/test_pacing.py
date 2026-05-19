from __future__ import annotations

import pytest

from agent.models import PacingProjection
from agent.pacing import project_budget_pacing


class TestProjectBudgetPacing:
    def test_on_pace(self):
        # 12h elapsed of 24h, spent 5000 of 10000 = exactly on pace
        result = project_budget_pacing("C1", 5000, 10000, 24, 12)
        assert result.pacing_status == "on_pace"
        assert result.projected_total_spend == pytest.approx(10000, abs=1)

    def test_under_pacing(self):
        # 12h elapsed, spent 3000 of 10000 → projected 6000 (60% of budget) = under-pacing
        result = project_budget_pacing("C1", 3000, 10000, 24, 12)
        assert result.pacing_status == "under_pacing"
        assert "increase" in result.recommendation.lower() or "broaden" in result.recommendation.lower()

    def test_over_pacing(self):
        # 12h elapsed, spent 7000 of 10000 → projected 14000 (140%) = over-pacing (not burnout, just above 115%)
        result = project_budget_pacing("C1", 6500, 10000, 24, 12)
        assert result.pacing_status in ("over_pacing", "burnout_risk")

    def test_burnout_risk(self):
        # 6h elapsed of 24, already spent 8000 of 10000 → projected 32000 = 320% burnout
        result = project_budget_pacing("C1", 8000, 10000, 24, 6)
        assert result.pacing_status == "burnout_risk"
        assert result.hours_to_exhaustion is not None

    def test_zero_elapsed_hours(self):
        result = project_budget_pacing("C1", 0, 10000, 24, 0)
        assert result.pacing_status == "under_pacing"
        assert result.projected_total_spend == 0.0

    def test_pct_values_correct(self):
        result = project_budget_pacing("C1", 2500, 10000, 24, 12)
        assert result.pct_budget_used == pytest.approx(25.0)
        assert result.pct_period_elapsed == pytest.approx(50.0)

    def test_campaign_id_preserved(self):
        result = project_budget_pacing("MY_CAMP", 5000, 10000, 24, 12)
        assert result.campaign_id == "MY_CAMP"

    def test_invalid_budget_raises(self):
        with pytest.raises(ValueError, match="total_budget must be positive"):
            project_budget_pacing("C1", 100, 0, 24, 12)

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError, match="period_hours must be positive"):
            project_budget_pacing("C1", 100, 10000, 0, 0)

    def test_elapsed_exceeds_period_raises(self):
        with pytest.raises(ValueError, match="elapsed_hours cannot exceed period_hours"):
            project_budget_pacing("C1", 100, 10000, 24, 25)

    def test_returns_pacing_projection_type(self):
        result = project_budget_pacing("C1", 5000, 10000, 24, 12)
        assert isinstance(result, PacingProjection)
