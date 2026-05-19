from __future__ import annotations

import pytest

from agent.models import CampaignDiagnosis, Issue, PrioritisedDiagnosis
from agent.prioritiser import _classify_effort, _compute_priority_score, prioritise_recommendations


def _make_issue(
    metric: str = "CPA",
    severity: str = "critical",
    root_cause: str = "Audience saturation.",
    recommendation: str = "Refresh creatives.",
    estimated_impact: str = "20% CPA reduction",
) -> Issue:
    return Issue(
        metric=metric,
        observed_value="420",
        expected_range="200-300",
        severity=severity,  # type: ignore[arg-type]
        root_cause=root_cause,
        recommendation=recommendation,
        estimated_impact=estimated_impact,
    )


def _make_diagnosis(issues: list[Issue]) -> CampaignDiagnosis:
    return CampaignDiagnosis(
        campaign_id="test",
        overall_health="critical" if any(i.severity == "critical" for i in issues) else "degraded",
        health_score=40,
        executive_summary="Test.",
        issues=issues,
        top_3_actions=[],
        positive_signals=[],
    )


class TestClassifyEffort:
    def test_bid_keyword_is_low_effort(self):
        issue = _make_issue(recommendation="Increase bids by 15% to improve win rate.")
        assert _classify_effort(issue) == "low"

    def test_frequency_cap_is_low_effort(self):
        issue = _make_issue(recommendation="Apply frequency cap of 3/week.")
        assert _classify_effort(issue) == "low"

    def test_creative_refresh_is_high_effort(self):
        issue = _make_issue(recommendation="Refresh creative assets with new visuals.")
        assert _classify_effort(issue) == "high"

    def test_tracking_fix_is_high_effort(self):
        issue = _make_issue(root_cause="Pixel tracking is broken.")
        assert _classify_effort(issue) == "high"

    def test_audience_issue_with_no_keywords_is_medium(self):
        issue = _make_issue(root_cause="Audience mismatch.", recommendation="Review targeting parameters.")
        assert _classify_effort(issue) == "medium"


class TestComputePriorityScore:
    def test_critical_gets_high_base(self):
        issue = _make_issue(severity="critical")
        score = _compute_priority_score(issue)
        assert score >= 85

    def test_warning_gets_mid_base(self):
        issue = _make_issue(severity="warning", metric="CTR")
        score = _compute_priority_score(issue)
        assert 55 <= score < 85

    def test_high_impact_metric_boosted(self):
        cpa_issue = _make_issue(metric="CPA", severity="warning")
        other_issue = _make_issue(metric="Viewability", severity="warning")
        assert _compute_priority_score(cpa_issue) > _compute_priority_score(other_issue)

    def test_score_capped_at_100(self):
        issue = _make_issue(metric="CPA", severity="critical", root_cause="spike in CPA")
        score = _compute_priority_score(issue)
        assert score <= 100


class TestPrioritiseRecommendations:
    def test_returns_prioritised_diagnosis(self):
        d = _make_diagnosis([_make_issue()])
        result = prioritise_recommendations(d)
        assert isinstance(result, PrioritisedDiagnosis)

    def test_issues_sorted_by_priority_score_descending(self):
        issues = [
            _make_issue(metric="CTR", severity="info"),
            _make_issue(metric="CPA", severity="critical"),
            _make_issue(metric="Win Rate", severity="warning"),
        ]
        result = prioritise_recommendations(_make_diagnosis(issues))
        scores = [i.priority_score for i in result.prioritised_issues]
        assert scores == sorted(scores, reverse=True)

    def test_quick_wins_are_low_effort_high_priority(self):
        issues = [
            _make_issue(
                metric="CPA", severity="critical",
                recommendation="Increase bids by 15%.",
            ),
            _make_issue(
                metric="Creative", severity="info",
                recommendation="Refresh creative assets.",
            ),
        ]
        result = prioritise_recommendations(_make_diagnosis(issues))
        # Only the critical+low-effort bid change should be a quick win
        assert len(result.quick_wins) >= 1
        assert any("bid" in qw.lower() or "increase" in qw.lower() for qw in result.quick_wins)

    def test_empty_issues_returns_empty_prioritised(self):
        d = _make_diagnosis([])
        result = prioritise_recommendations(d)
        assert result.prioritised_issues == []
        assert result.quick_wins == []

    def test_campaign_id_preserved(self):
        d = _make_diagnosis([_make_issue()])
        result = prioritise_recommendations(d)
        assert result.campaign_id == "test"
