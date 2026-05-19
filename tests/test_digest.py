from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent.digest import generate_weekly_digest
from agent.models import CampaignDiagnosis, Issue, WeeklyDigest


def _make_diagnosis(
    campaign_id: str,
    health: str = "healthy",
    score: int = 80,
    issues: list | None = None,
) -> CampaignDiagnosis:
    return CampaignDiagnosis(
        campaign_id=campaign_id,
        campaign_name=f"Campaign {campaign_id}",
        overall_health=health,  # type: ignore[arg-type]
        health_score=score,
        executive_summary="Test summary.",
        issues=issues or [],
        top_3_actions=["Action 1"],
        positive_signals=[],
    )


def _make_issue(metric: str = "CPA") -> Issue:
    return Issue(
        metric=metric,
        observed_value="420",
        expected_range="200-300",
        severity="critical",
        root_cause="Test root cause.",
        recommendation="Test recommendation.",
        estimated_impact="20% improvement",
    )


def _mock_client(text: str = "Weekly fleet summary.") -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    client.messages.create.return_value = msg
    return client


class TestGenerateWeeklyDigest:
    def test_returns_weekly_digest(self):
        diagnoses = [_make_diagnosis("A")]
        result = generate_weekly_digest(diagnoses, client=_mock_client())
        assert isinstance(result, WeeklyDigest)

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            generate_weekly_digest([], client=_mock_client())

    def test_counts_health_statuses(self):
        diagnoses = [
            _make_diagnosis("A", "healthy"),
            _make_diagnosis("B", "healthy"),
            _make_diagnosis("C", "degraded"),
            _make_diagnosis("D", "critical"),
        ]
        result = generate_weekly_digest(diagnoses, client=_mock_client())
        assert result.healthy == 2
        assert result.degraded == 1
        assert result.critical == 1
        assert result.total_campaigns == 4

    def test_fleet_average_score(self):
        diagnoses = [
            _make_diagnosis("A", score=80),
            _make_diagnosis("B", score=60),
        ]
        result = generate_weekly_digest(diagnoses, client=_mock_client())
        assert result.fleet_average_score == pytest.approx(70.0)

    def test_most_common_issues_populated(self):
        issues_a = [_make_issue("CPA"), _make_issue("Win Rate")]
        issues_b = [_make_issue("CPA")]
        diagnoses = [
            _make_diagnosis("A", "critical", 30, issues_a),
            _make_diagnosis("B", "degraded", 50, issues_b),
        ]
        result = generate_weekly_digest(diagnoses, client=_mock_client())
        assert "CPA" in result.most_common_issues
        assert result.most_common_issues[0] == "CPA"

    def test_week_label_preserved(self):
        diagnoses = [_make_diagnosis("A")]
        result = generate_weekly_digest(diagnoses, week_label="2026-W20", client=_mock_client())
        assert result.week_label == "2026-W20"

    def test_campaign_summaries_length(self):
        diagnoses = [_make_diagnosis("A"), _make_diagnosis("B"), _make_diagnosis("C")]
        result = generate_weekly_digest(diagnoses, client=_mock_client())
        assert len(result.campaign_summaries) == 3

    def test_top_issue_populated_from_first_issue(self):
        issues = [_make_issue("Frequency"), _make_issue("CTR")]
        diagnoses = [_make_diagnosis("A", "degraded", 50, issues)]
        result = generate_weekly_digest(diagnoses, client=_mock_client())
        assert result.campaign_summaries[0].top_issue == "Frequency"

    def test_digest_summary_comes_from_llm(self):
        diagnoses = [_make_diagnosis("A")]
        client = _mock_client("Fleet is in good shape this week.")
        result = generate_weekly_digest(diagnoses, client=client)
        assert "Fleet is in good shape" in result.digest_summary

    def test_llm_called_once_for_summary(self):
        diagnoses = [_make_diagnosis("A"), _make_diagnosis("B")]
        client = _mock_client()
        generate_weekly_digest(diagnoses, client=client)
        assert client.messages.create.call_count == 1
