from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from agent.diagnostician import compare_campaigns
from agent.models import CampaignComparison, CampaignMetrics


def _metrics(campaign_id: str, **kwargs) -> CampaignMetrics:
    defaults = dict(spend=10000, impressions=500000, clicks=600, ctr=0.12, cpa=250, win_rate=30, frequency=4, roas=2.5)
    defaults.update(kwargs)
    return CampaignMetrics(campaign_id=campaign_id, **defaults)


def _mock_client(payload: dict) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    client.messages.create.return_value = msg
    return client


_DEFAULT_LLM = {
    "overall_winner": "camp_a",
    "comparison_narrative": "Campaign A outperforms B on CTR and ROAS.",
    "key_differentiators": ["Higher CTR", "Better ROAS"],
}


class TestCompareCampaigns:
    def test_returns_campaign_comparison(self):
        client = _mock_client(_DEFAULT_LLM)
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert isinstance(result, CampaignComparison)

    def test_campaign_ids_preserved(self):
        client = _mock_client(_DEFAULT_LLM)
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert result.campaign_a_id == "camp_a"
        assert result.campaign_b_id == "camp_b"

    def test_metric_deltas_computed(self):
        client = _mock_client(_DEFAULT_LLM)
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert len(result.metric_deltas) > 0
        metrics_listed = [d.metric for d in result.metric_deltas]
        assert any("CTR" in m for m in metrics_listed)

    def test_winner_from_llm_response(self):
        llm = {**_DEFAULT_LLM, "overall_winner": "camp_a"}
        client = _mock_client(llm)
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert result.overall_winner == "camp_a"

    def test_invalid_winner_defaults_to_none(self):
        llm = {**_DEFAULT_LLM, "overall_winner": "some_other_campaign"}
        client = _mock_client(llm)
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert result.overall_winner is None

    def test_key_differentiators_populated(self):
        client = _mock_client(_DEFAULT_LLM)
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert len(result.key_differentiators) > 0

    def test_comparison_narrative_populated(self):
        client = _mock_client(_DEFAULT_LLM)
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert len(result.comparison_narrative) > 0

    def test_advantage_a_when_a_has_better_cpa(self):
        # lower CPA is better for campaign A
        a = _metrics("camp_a", cpa=200)
        b = _metrics("camp_b", cpa=400)
        client = _mock_client(_DEFAULT_LLM)
        result = compare_campaigns(a, b, client=client)
        cpa_delta = next((d for d in result.metric_deltas if "CPA" in d.metric), None)
        assert cpa_delta is not None
        assert cpa_delta.advantage == "a"

    def test_advantage_b_when_b_has_better_roas(self):
        a = _metrics("camp_a", roas=1.5)
        b = _metrics("camp_b", roas=3.5)
        client = _mock_client(_DEFAULT_LLM)
        result = compare_campaigns(a, b, client=client)
        roas_delta = next((d for d in result.metric_deltas if "ROAS" in d.metric), None)
        assert roas_delta is not None
        assert roas_delta.advantage == "b"

    def test_invalid_json_from_llm_handled_gracefully(self):
        client = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text="This is not valid JSON.")]
        client.messages.create.return_value = msg
        result = compare_campaigns(_metrics("camp_a"), _metrics("camp_b"), client=client)
        assert isinstance(result, CampaignComparison)
        assert result.overall_winner is None
