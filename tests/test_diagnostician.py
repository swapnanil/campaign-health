from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agent.diagnostician import diagnose_batch, diagnose_campaign
from agent.models import BatchDiagnosis, CampaignDiagnosis


def _make_mock_client(response_json: dict | None = None) -> MagicMock:
    """Return a mock Anthropic client that returns the given JSON as the LLM text."""
    if response_json is None:
        response_json = {
            "campaign_id": "test",
            "campaign_name": None,
            "overall_health": "healthy",
            "health_score": 85,
            "executive_summary": "Campaign is performing well.",
            "issues": [],
            "top_3_actions": ["Monitor frequency weekly"],
            "positive_signals": ["Strong CTR above benchmark"],
        }

    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(response_json))]
    mock_client.messages.create.return_value = mock_message
    return mock_client


class TestDiagnoseGoodCampaign:
    def test_healthy_campaign_returns_diagnosis(self, good_metrics):
        response = {
            "campaign_id": "camp_003",
            "campaign_name": "Search Retargeting Premium",
            "overall_health": "healthy",
            "health_score": 92,
            "executive_summary": "This search retargeting campaign is performing at an excellent level with strong ROAS and CTR well above benchmark.",
            "issues": [],
            "top_3_actions": ["Continue current strategy", "Monitor frequency weekly", "Test new ad variations"],
            "positive_signals": ["CTR 3.2% far above search benchmark of 2%", "ROAS 2.8x is excellent", "Win rate 42% is healthy"],
        }
        client = _make_mock_client(response)
        result = diagnose_campaign(good_metrics, client=client)
        assert isinstance(result, CampaignDiagnosis)
        assert result.overall_health == "healthy"
        assert result.health_score >= 80
        assert len(result.positive_signals) > 0

    def test_healthy_campaign_has_no_critical_issues(self, good_metrics):
        response = {
            "campaign_id": "camp_003",
            "campaign_name": "Search Retargeting Premium",
            "overall_health": "healthy",
            "health_score": 92,
            "executive_summary": "Performing well.",
            "issues": [],
            "top_3_actions": ["Keep going"],
            "positive_signals": ["Strong ROAS"],
        }
        client = _make_mock_client(response)
        result = diagnose_campaign(good_metrics, client=client)
        critical = [i for i in result.issues if i.severity == "critical"]
        assert len(critical) == 0


class TestDiagnoseCpaSpike:
    def test_cpa_spike_returns_critical(self, cpa_spike_latest_metrics, cpa_spike_prior_metrics):
        response = {
            "campaign_id": "camp_001",
            "campaign_name": "Display Retargeting Q1",
            "overall_health": "critical",
            "health_score": 28,
            "executive_summary": "CPA spiked 68% WoW due to ad fatigue from frequency 9.2.",
            "issues": [
                {
                    "metric": "CPA",
                    "observed_value": "₹420 (↑68% WoW)",
                    "expected_range": "₹200–₹280",
                    "severity": "critical",
                    "root_cause": "Audience saturation from high frequency.",
                    "recommendation": "Apply frequency cap of 3/week.",
                    "estimated_impact": "25–40% CPA reduction",
                },
                {
                    "metric": "Frequency",
                    "observed_value": "9.2",
                    "expected_range": "3–5",
                    "severity": "critical",
                    "root_cause": "No frequency cap set.",
                    "recommendation": "Cap at 3/day.",
                    "estimated_impact": "40% waste reduction",
                },
            ],
            "top_3_actions": ["Set frequency cap", "Refresh creatives", "Expand audience"],
            "positive_signals": ["Win rate healthy at 35%"],
        }
        client = _make_mock_client(response)
        result = diagnose_campaign(cpa_spike_latest_metrics, client=client, prior_period=cpa_spike_prior_metrics)
        assert result.overall_health == "critical"
        assert any(i.metric == "CPA" for i in result.issues)

    def test_prior_period_triggers_wow_computation(self, cpa_spike_latest_metrics, cpa_spike_prior_metrics):
        response = {
            "campaign_id": "camp_001",
            "campaign_name": "Display Retargeting Q1",
            "overall_health": "critical",
            "health_score": 25,
            "executive_summary": "Critical ad fatigue.",
            "issues": [],
            "top_3_actions": ["Fix frequency"],
            "positive_signals": [],
        }
        client = _make_mock_client(response)
        # The call should succeed and pass WoW data to LLM
        result = diagnose_campaign(cpa_spike_latest_metrics, client=client, prior_period=cpa_spike_prior_metrics)
        assert result is not None
        # Verify prompt included WoW data by checking the call args
        call_args = client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]
        assert "WoW" in user_content or "wow" in user_content.lower()


class TestDiagnoseLowCtr:
    def test_low_ctr_bid_below_floor_detected(self, low_ctr_metrics):
        response = {
            "campaign_id": "camp_002",
            "campaign_name": "Native Awareness Drive",
            "overall_health": "degraded",
            "health_score": 45,
            "executive_summary": "Bidding below floor price is causing low win rate and CTR is 70% below benchmark.",
            "issues": [
                {
                    "metric": "Win Rate",
                    "observed_value": "12%",
                    "expected_range": "25–40%",
                    "severity": "critical",
                    "root_cause": "Avg bid ₹15 is below floor price ₹18.",
                    "recommendation": "Raise avg bid above ₹18.",
                    "estimated_impact": "Win rate doubles to 24%+",
                },
                {
                    "metric": "CTR",
                    "observed_value": "0.03%",
                    "expected_range": "0.10–0.15%",
                    "severity": "warning",
                    "root_cause": "Weak creative and poor audience match.",
                    "recommendation": "Refresh native ad creative with stronger headline.",
                    "estimated_impact": "50–100% CTR improvement",
                },
            ],
            "top_3_actions": ["Raise bid above floor price", "Refresh creative", "Improve audience targeting"],
            "positive_signals": ["CPA of ₹250 is within acceptable range"],
        }
        client = _make_mock_client(response)
        result = diagnose_campaign(low_ctr_metrics, client=client)
        assert result.overall_health in ("degraded", "critical")
        assert any("win" in i.metric.lower() or "ctr" in i.metric.lower() for i in result.issues)


class TestInvalidJsonRetry:
    def test_retries_on_invalid_json(self, good_metrics):
        good_response = {
            "campaign_id": "camp_003",
            "campaign_name": None,
            "overall_health": "healthy",
            "health_score": 88,
            "executive_summary": "Good campaign.",
            "issues": [],
            "top_3_actions": ["Keep going"],
            "positive_signals": ["Strong performance"],
        }
        mock_client = MagicMock()
        bad_message = MagicMock()
        bad_message.content = [MagicMock(text="This is not JSON at all.")]
        good_message = MagicMock()
        good_message.content = [MagicMock(text=json.dumps(good_response))]
        mock_client.messages.create.side_effect = [bad_message, good_message]

        result = diagnose_campaign(good_metrics, client=mock_client)
        assert result.overall_health == "healthy"
        assert mock_client.messages.create.call_count == 2


class TestDataQualityRejection:
    def test_zero_metrics_raises(self):
        from agent.models import CampaignMetrics
        m = CampaignMetrics(campaign_id="x", spend=0, impressions=0, clicks=0)
        with pytest.raises(ValueError, match="insufficient data"):
            diagnose_campaign(m, client=MagicMock())


class TestBatchDiagnosis:
    def test_batch_returns_batch_diagnosis(self, good_metrics, low_ctr_metrics):
        good_resp = {
            "campaign_id": "camp_003", "campaign_name": None, "overall_health": "healthy",
            "health_score": 90, "executive_summary": "Good.", "issues": [],
            "top_3_actions": ["Continue"], "positive_signals": ["Strong ROAS"],
        }
        low_ctr_resp = {
            "campaign_id": "camp_002", "campaign_name": None, "overall_health": "degraded",
            "health_score": 45, "executive_summary": "Low CTR.", "issues": [],
            "top_3_actions": ["Fix bids"], "positive_signals": [],
        }
        fleet_text = "Two campaigns analysed. Camp_002 has structural bid issues while camp_003 is healthy."

        mock_client = MagicMock()
        responses = [good_resp, low_ctr_resp]
        call_count = [0]

        def side_effect(**kwargs):
            msg = MagicMock()
            if call_count[0] < len(responses):
                msg.content = [MagicMock(text=json.dumps(responses[call_count[0]]))]
            else:
                msg.content = [MagicMock(text=fleet_text)]
            call_count[0] += 1
            return msg

        mock_client.messages.create.side_effect = side_effect

        result = diagnose_batch([good_metrics, low_ctr_metrics], client=mock_client)
        assert isinstance(result, BatchDiagnosis)
        assert len(result.campaigns) == 2
        assert result.fleet_summary != ""
