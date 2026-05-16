from __future__ import annotations

from pathlib import Path

import pytest

from agent.models import CampaignMetrics

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture
def good_csv_path() -> Path:
    return EXAMPLES_DIR / "sample_campaign_good.csv"


@pytest.fixture
def cpa_spike_csv_path() -> Path:
    return EXAMPLES_DIR / "sample_campaign_cpa_spike.csv"


@pytest.fixture
def low_ctr_csv_path() -> Path:
    return EXAMPLES_DIR / "sample_campaign_low_ctr.csv"


@pytest.fixture
def good_metrics() -> CampaignMetrics:
    return CampaignMetrics(
        campaign_id="camp_003",
        campaign_name="Search Retargeting Premium",
        date_range="2024-01-22 to 2024-01-28",
        impressions=125000,
        clicks=4000,
        conversions=200,
        spend=36000,
        ctr=3.2,
        cpc=9.0,
        cpa=180,
        cvr=5.0,
        win_rate=42,
        avg_bid=28,
        floor_price=16,
        roas=2.8,
        viewability=82,
        frequency=3.0,
        budget_utilisation=97,
    )


@pytest.fixture
def cpa_spike_latest_metrics() -> CampaignMetrics:
    return CampaignMetrics(
        campaign_id="camp_001",
        campaign_name="Display Retargeting Q1",
        date_range="2024-01-22 to 2024-01-28",
        impressions=870000,
        clicks=870,
        conversions=52,
        spend=21840,
        ctr=0.10,
        cpc=25.10,
        cpa=420,
        win_rate=35,
        avg_bid=22,
        floor_price=14,
        roas=1.38,
        viewability=63,
        frequency=9.2,
        budget_utilisation=95,
    )


@pytest.fixture
def cpa_spike_prior_metrics() -> CampaignMetrics:
    return CampaignMetrics(
        campaign_id="camp_001",
        campaign_name="Display Retargeting Q1",
        date_range="2024-01-15 to 2024-01-21",
        impressions=910000,
        clicks=1092,
        conversions=72,
        spend=18200,
        ctr=0.12,
        cpc=16.67,
        cpa=252.8,
        win_rate=36,
        avg_bid=22,
        floor_price=14,
        roas=2.35,
        viewability=66,
        frequency=6.9,
        budget_utilisation=94,
    )


@pytest.fixture
def low_ctr_metrics() -> CampaignMetrics:
    return CampaignMetrics(
        campaign_id="camp_002",
        campaign_name="Native Awareness Drive",
        date_range="2024-01-22 to 2024-01-28",
        impressions=2400000,
        clicks=720,
        conversions=36,
        spend=9000,
        ctr=0.03,
        cpc=12.5,
        cpa=250,
        cvr=5.0,
        win_rate=12,
        avg_bid=15,
        floor_price=18,
        roas=1.8,
        viewability=71,
        frequency=2.1,
        budget_utilisation=58,
    )
