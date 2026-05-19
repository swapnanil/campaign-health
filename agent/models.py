from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CampaignMetrics(BaseModel):
    campaign_id: str
    campaign_name: str | None = None
    date_range: str | None = None
    impressions: float | None = None
    clicks: float | None = None
    conversions: float | None = None
    spend: float
    ctr: float | None = None          # clicks / impressions (%)
    cpc: float | None = None          # cost per click
    cpa: float | None = None          # cost per acquisition
    cvr: float | None = None          # conversion rate (%)
    win_rate: float | None = None     # bid wins / bid attempts (%)
    avg_bid: float | None = None      # average bid submitted
    floor_price: float | None = None  # auction floor price
    roas: float | None = None         # return on ad spend
    viewability: float | None = None  # % impressions that were viewable
    frequency: float | None = None    # avg impressions per unique user
    budget_utilisation: float | None = None  # spend / budget (%)

    @field_validator("spend")
    @classmethod
    def spend_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("spend cannot be negative")
        return v


class PreprocessedMetrics(CampaignMetrics):
    # Derived ratios
    ctr_computed: float | None = None
    cpc_computed: float | None = None
    cpa_computed: float | None = None
    cvr_computed: float | None = None

    # WoW changes (% change vs prior period)
    cpa_wow_change: float | None = None
    ctr_wow_change: float | None = None
    spend_wow_change: float | None = None

    # Anomaly flags
    ctr_below_benchmark: bool = False
    win_rate_critical: bool = False
    win_rate_concern: bool = False
    cpa_spike: bool = False
    budget_underpacing: bool = False
    frequency_fatigue: bool = False
    roas_critical: bool = False
    bid_below_floor: bool = False

    # Benchmark deltas (% from benchmark)
    ctr_delta_pct: float | None = None
    win_rate_delta_pct: float | None = None

    # Pacing
    pacing_status: Literal["on_pace", "under_pacing", "over_pacing", "unknown"] = "unknown"

    # Thresholds used (may be overridden via CLI)
    ctr_benchmark: float = 0.1
    cpa_target: float | None = None


class Issue(BaseModel):
    metric: str
    observed_value: str
    expected_range: str
    severity: Literal["critical", "warning", "info"]
    root_cause: str
    recommendation: str
    estimated_impact: str


class CampaignDiagnosis(BaseModel):
    campaign_id: str
    campaign_name: str | None = None
    overall_health: Literal["healthy", "degraded", "critical"]
    health_score: int = Field(ge=0, le=100)
    executive_summary: str
    issues: list[Issue]
    top_3_actions: list[str]
    positive_signals: list[str]


class BatchDiagnosis(BaseModel):
    campaigns: list[CampaignDiagnosis]
    fleet_summary: str


class HealthResponse(BaseModel):
    status: str
    model: str


class BenchmarkResponse(BaseModel):
    ctr_benchmark_display_pct: float
    ctr_benchmark_search_pct: float
    win_rate_concern_threshold_pct: float
    win_rate_critical_threshold_pct: float
    frequency_fatigue_threshold: float
    cpa_spike_threshold_pct: float
    budget_underpacing_threshold_pct: float
    roas_critical_threshold: float


# Feature 1: Alert Rules Engine
class AlertRule(BaseModel):
    metric: str
    condition: Literal["gt", "lt", "gte", "lte"]
    threshold: float
    severity: Literal["critical", "warning", "info"]
    label: str


class AlertTrigger(BaseModel):
    rule_label: str
    metric: str
    observed_value: float
    threshold: float
    condition: str
    severity: Literal["critical", "warning", "info"]
    message: str


class AlertReport(BaseModel):
    campaign_id: str
    triggers: list[AlertTrigger]
    total_alerts: int
    highest_severity: Literal["critical", "warning", "info", "none"]
    alert_summary: str


# Feature 2: Budget Pacing Projection
class PacingProjection(BaseModel):
    campaign_id: str
    current_spend: float
    total_budget: float
    pct_budget_used: float
    pct_period_elapsed: float
    projected_total_spend: float
    pacing_status: Literal["on_pace", "under_pacing", "over_pacing", "burnout_risk"]
    hours_to_exhaustion: float | None = None
    recommendation: str


# Feature 3: Vertical Benchmarks
class VerticalBenchmarks(BaseModel):
    vertical: str
    ctr_display_pct: float
    ctr_search_pct: float
    win_rate_healthy_pct: float
    roas_target: float
    frequency_fatigue_threshold: float
    description: str


# Feature 4: Recommendation Prioritiser
class PrioritisedIssue(BaseModel):
    metric: str
    severity: Literal["critical", "warning", "info"]
    root_cause: str
    recommendation: str
    estimated_impact: str
    effort: Literal["low", "medium", "high"]
    priority_score: int = Field(ge=0, le=100)


class PrioritisedDiagnosis(BaseModel):
    campaign_id: str
    overall_health: Literal["healthy", "degraded", "critical"]
    health_score: int
    prioritised_issues: list[PrioritisedIssue]
    quick_wins: list[str]


# Feature 5: Weekly Digest
class CampaignSummary(BaseModel):
    campaign_id: str
    campaign_name: str | None = None
    overall_health: Literal["healthy", "degraded", "critical"]
    health_score: int
    top_issue: str | None = None


class WeeklyDigest(BaseModel):
    week_label: str | None = None
    total_campaigns: int
    healthy: int
    degraded: int
    critical: int
    fleet_average_score: float
    most_common_issues: list[str]
    campaign_summaries: list[CampaignSummary]
    digest_summary: str


# Feature 6: Campaign Comparison
class MetricDelta(BaseModel):
    metric: str
    campaign_a_value: str
    campaign_b_value: str
    advantage: Literal["a", "b", "parity"]


class CampaignComparison(BaseModel):
    campaign_a_id: str
    campaign_b_id: str
    metric_deltas: list[MetricDelta]
    overall_winner: str | None = None
    comparison_narrative: str
    key_differentiators: list[str]
