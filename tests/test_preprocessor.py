from __future__ import annotations

import pytest

from agent.models import CampaignMetrics
from agent.preprocessor import (
    aggregate_campaign,
    group_by_campaign,
    load_csv,
    preprocess,
    validate_metrics,
)


class TestDerivedRatios:
    def test_ctr_computed_from_clicks_impressions(self):
        m = CampaignMetrics(campaign_id="x", spend=1000, impressions=100000, clicks=100)
        pre = preprocess(m)
        assert pre.ctr_computed == pytest.approx(0.1, rel=1e-3)

    def test_ctr_not_recomputed_when_provided(self):
        m = CampaignMetrics(campaign_id="x", spend=1000, impressions=100000, clicks=100, ctr=0.15)
        pre = preprocess(m)
        assert pre.ctr_computed == 0.15

    def test_cpc_computed(self):
        m = CampaignMetrics(campaign_id="x", spend=5000, clicks=200)
        pre = preprocess(m)
        assert pre.cpc_computed == pytest.approx(25.0)

    def test_cpa_computed(self):
        m = CampaignMetrics(campaign_id="x", spend=10000, conversions=50)
        pre = preprocess(m)
        assert pre.cpa_computed == pytest.approx(200.0)

    def test_cvr_computed(self):
        m = CampaignMetrics(campaign_id="x", spend=5000, clicks=500, conversions=25)
        pre = preprocess(m)
        assert pre.cvr_computed == pytest.approx(5.0)

    def test_no_division_by_zero_on_zero_clicks(self):
        m = CampaignMetrics(campaign_id="x", spend=1000, impressions=50000, clicks=0)
        pre = preprocess(m)
        assert pre.ctr_computed == pytest.approx(0.0)
        assert pre.cpc_computed is None  # can't divide by 0 clicks


class TestAnomalyFlags:
    def test_ctr_below_benchmark_flagged(self, low_ctr_metrics):
        pre = preprocess(low_ctr_metrics, ctr_benchmark=0.1)
        assert pre.ctr_below_benchmark is True

    def test_ctr_above_benchmark_not_flagged(self, good_metrics):
        pre = preprocess(good_metrics, ctr_benchmark=0.1)
        assert pre.ctr_below_benchmark is False

    def test_win_rate_critical(self):
        m = CampaignMetrics(campaign_id="x", spend=5000, win_rate=8)
        pre = preprocess(m)
        assert pre.win_rate_critical is True
        assert pre.win_rate_concern is True

    def test_win_rate_concern_not_critical(self):
        m = CampaignMetrics(campaign_id="x", spend=5000, win_rate=15)
        pre = preprocess(m)
        assert pre.win_rate_critical is False
        assert pre.win_rate_concern is True

    def test_win_rate_healthy(self, good_metrics):
        pre = preprocess(good_metrics)
        assert pre.win_rate_critical is False
        assert pre.win_rate_concern is False

    def test_frequency_fatigue_flagged(self, cpa_spike_latest_metrics):
        pre = preprocess(cpa_spike_latest_metrics)
        assert pre.frequency_fatigue is True

    def test_frequency_healthy(self, good_metrics):
        pre = preprocess(good_metrics)
        assert pre.frequency_fatigue is False

    def test_roas_critical_below_one(self):
        m = CampaignMetrics(campaign_id="x", spend=5000, roas=0.7)
        pre = preprocess(m)
        assert pre.roas_critical is True

    def test_roas_healthy(self, good_metrics):
        pre = preprocess(good_metrics)
        assert pre.roas_critical is False

    def test_bid_below_floor(self, low_ctr_metrics):
        pre = preprocess(low_ctr_metrics)
        assert pre.bid_below_floor is True

    def test_bid_above_floor(self, good_metrics):
        pre = preprocess(good_metrics)
        assert pre.bid_below_floor is False

    def test_budget_underpacing(self, low_ctr_metrics):
        pre = preprocess(low_ctr_metrics)
        assert pre.budget_underpacing is True
        assert pre.pacing_status == "under_pacing"

    def test_budget_on_pace(self, good_metrics):
        pre = preprocess(good_metrics)
        assert pre.budget_underpacing is False
        assert pre.pacing_status == "on_pace"


class TestWoWChanges:
    def test_cpa_wow_spike_detected(self, cpa_spike_latest_metrics, cpa_spike_prior_metrics):
        pre = preprocess(cpa_spike_latest_metrics, prior_period=cpa_spike_prior_metrics)
        assert pre.cpa_wow_change is not None
        assert pre.cpa_wow_change > 40
        assert pre.cpa_spike is True

    def test_no_wow_without_prior(self, cpa_spike_latest_metrics):
        pre = preprocess(cpa_spike_latest_metrics)
        assert pre.cpa_wow_change is None
        assert pre.cpa_spike is False


class TestValidation:
    def test_all_zero_rejected(self):
        m = CampaignMetrics(campaign_id="x", spend=0, impressions=0, clicks=0)
        errors = validate_metrics(m)
        assert any("insufficient data" in e.lower() for e in errors)

    def test_negative_spend_flagged(self):
        with pytest.raises(Exception):
            CampaignMetrics(campaign_id="x", spend=-100)

    def test_impossible_ctr_flagged(self):
        m = CampaignMetrics(campaign_id="x", spend=1000, ctr=150)
        errors = validate_metrics(m)
        assert any("ctr" in e.lower() for e in errors)

    def test_clicks_exceed_impressions(self):
        m = CampaignMetrics(campaign_id="x", spend=1000, impressions=100, clicks=200)
        errors = validate_metrics(m)
        assert any("clicks" in e.lower() for e in errors)

    def test_valid_metrics_no_errors(self, good_metrics):
        errors = validate_metrics(good_metrics)
        assert errors == []


class TestCsvLoading:
    def test_load_good_csv(self, good_csv_path):
        records = load_csv(str(good_csv_path))
        assert len(records) == 1
        assert records[0].campaign_id == "camp_003"

    def test_load_multi_row_cpa_spike_csv(self, cpa_spike_csv_path):
        records = load_csv(str(cpa_spike_csv_path))
        assert len(records) == 4
        assert all(r.campaign_id == "camp_001" for r in records)

    def test_load_low_ctr_csv(self, low_ctr_csv_path):
        records = load_csv(str(low_ctr_csv_path))
        assert len(records) == 1
        assert records[0].win_rate == pytest.approx(12)

    def test_missing_required_column_raises(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("campaign_id,impressions\nc1,10000\n")
        with pytest.raises(ValueError, match="spend"):
            load_csv(str(bad_csv))


class TestGroupAndAggregate:
    def test_group_by_campaign(self, cpa_spike_csv_path):
        records = load_csv(str(cpa_spike_csv_path))
        grouped = group_by_campaign(records)
        assert "camp_001" in grouped
        assert len(grouped["camp_001"]) == 4

    def test_aggregate_returns_latest_and_prior(self, cpa_spike_csv_path):
        records = load_csv(str(cpa_spike_csv_path))
        grouped = group_by_campaign(records)
        latest, prior = aggregate_campaign(grouped["camp_001"])
        assert latest is not None
        assert prior is not None
        assert latest.date_range > prior.date_range  # latest date is greater

    def test_aggregate_single_row_returns_none_prior(self, good_csv_path):
        records = load_csv(str(good_csv_path))
        latest, prior = aggregate_campaign(records)
        assert prior is None
