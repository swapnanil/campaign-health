from __future__ import annotations

import os
from typing import Any

import pandas as pd

from agent.models import CampaignMetrics, PreprocessedMetrics

# Industry benchmark defaults (overridable via env or CLI args)
CTR_BENCHMARK_DISPLAY = float(os.getenv("CTR_BENCHMARK_DISPLAY", "0.1"))
CTR_BENCHMARK_SEARCH = float(os.getenv("CTR_BENCHMARK_SEARCH", "2.0"))

WIN_RATE_CONCERN = 20.0
WIN_RATE_CRITICAL = 10.0
FREQUENCY_FATIGUE = 7.0
CPA_SPIKE_THRESHOLD = 40.0  # % WoW
BUDGET_UNDERPACING = 70.0
ROAS_CRITICAL = 1.0


def preprocess(
    metrics: CampaignMetrics,
    ctr_benchmark: float = CTR_BENCHMARK_DISPLAY,
    cpa_target: float | None = None,
    prior_period: CampaignMetrics | None = None,
) -> PreprocessedMetrics:
    data = metrics.model_dump()
    pre = PreprocessedMetrics(**data)
    pre.ctr_benchmark = ctr_benchmark
    pre.cpa_target = cpa_target

    # --- Derived ratios ---
    if pre.ctr is None and pre.impressions and pre.clicks is not None:
        if pre.impressions > 0:
            pre.ctr_computed = round((pre.clicks / pre.impressions) * 100, 4)
    else:
        pre.ctr_computed = pre.ctr

    if pre.cpc is None and pre.clicks and pre.clicks > 0:
        pre.cpc_computed = round(pre.spend / pre.clicks, 2)
    else:
        pre.cpc_computed = pre.cpc

    if pre.cpa is None and pre.conversions and pre.conversions > 0:
        pre.cpa_computed = round(pre.spend / pre.conversions, 2)
    else:
        pre.cpa_computed = pre.cpa

    if pre.cvr is None and pre.clicks and pre.clicks > 0 and pre.conversions is not None:
        pre.cvr_computed = round((pre.conversions / pre.clicks) * 100, 4)
    else:
        pre.cvr_computed = pre.cvr

    effective_ctr = pre.ctr_computed or pre.ctr
    effective_cpa = pre.cpa_computed or pre.cpa

    # --- WoW changes ---
    if prior_period is not None:
        pp = preprocess(prior_period, ctr_benchmark=ctr_benchmark)
        prior_cpa = pp.cpa_computed or pp.cpa
        prior_ctr = pp.ctr_computed or pp.ctr

        if prior_cpa and prior_cpa > 0 and effective_cpa is not None:
            pre.cpa_wow_change = round(((effective_cpa - prior_cpa) / prior_cpa) * 100, 1)

        if prior_ctr and prior_ctr > 0 and effective_ctr is not None:
            pre.ctr_wow_change = round(((effective_ctr - prior_ctr) / prior_ctr) * 100, 1)

        if prior_period.spend > 0:
            pre.spend_wow_change = round(((pre.spend - prior_period.spend) / prior_period.spend) * 100, 1)

    # --- Anomaly flags ---
    if effective_ctr is not None:
        pre.ctr_below_benchmark = effective_ctr < ctr_benchmark
        pre.ctr_delta_pct = round(((effective_ctr - ctr_benchmark) / ctr_benchmark) * 100, 1) if ctr_benchmark else None

    if pre.win_rate is not None:
        pre.win_rate_critical = pre.win_rate < WIN_RATE_CRITICAL
        pre.win_rate_concern = pre.win_rate < WIN_RATE_CONCERN
        healthy_win_rate = 30.0
        pre.win_rate_delta_pct = round(((pre.win_rate - healthy_win_rate) / healthy_win_rate) * 100, 1)

    if pre.cpa_wow_change is not None:
        pre.cpa_spike = pre.cpa_wow_change > CPA_SPIKE_THRESHOLD

    if pre.budget_utilisation is not None:
        pre.budget_underpacing = pre.budget_utilisation < BUDGET_UNDERPACING
        if pre.budget_utilisation < BUDGET_UNDERPACING:
            pre.pacing_status = "under_pacing"
        elif pre.budget_utilisation > 100:
            pre.pacing_status = "over_pacing"
        else:
            pre.pacing_status = "on_pace"

    if pre.frequency is not None:
        pre.frequency_fatigue = pre.frequency > FREQUENCY_FATIGUE

    if pre.roas is not None:
        pre.roas_critical = pre.roas < ROAS_CRITICAL

    if pre.avg_bid is not None and pre.floor_price is not None:
        pre.bid_below_floor = pre.avg_bid < pre.floor_price

    return pre


def validate_metrics(metrics: CampaignMetrics) -> list[str]:
    errors = []

    if metrics.spend == 0 and metrics.impressions == 0 and metrics.clicks == 0:
        errors.append("All zero metrics — insufficient data to diagnose.")

    if metrics.spend < 0:
        errors.append("spend is negative — data quality issue.")

    if metrics.ctr is not None and not (0 <= metrics.ctr <= 100):
        errors.append(f"CTR {metrics.ctr} is out of valid range (0–100%).")

    if metrics.win_rate is not None and not (0 <= metrics.win_rate <= 100):
        errors.append(f"Win rate {metrics.win_rate} is out of valid range (0–100%).")

    if metrics.roas is not None and metrics.roas < 0:
        errors.append(f"ROAS {metrics.roas} is negative — impossible value.")

    if metrics.impressions is not None and metrics.clicks is not None:
        if metrics.clicks > metrics.impressions:
            errors.append("clicks > impressions — impossible ratio, likely data quality issue.")

    return errors


REQUIRED_COLUMNS = {"campaign_id", "spend"}


def load_csv(path: str) -> list[CampaignMetrics]:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

    records: list[CampaignMetrics] = []
    for _, row in df.iterrows():
        row_dict = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        # campaign_id must be string
        row_dict["campaign_id"] = str(row_dict["campaign_id"])
        records.append(CampaignMetrics(**row_dict))

    return records


def group_by_campaign(records: list[CampaignMetrics]) -> dict[str, list[CampaignMetrics]]:
    grouped: dict[str, list[CampaignMetrics]] = {}
    for r in records:
        grouped.setdefault(r.campaign_id, []).append(r)
    return grouped


def aggregate_campaign(rows: list[CampaignMetrics]) -> tuple[CampaignMetrics, CampaignMetrics | None]:
    """Return (latest_period, prior_period_or_None) for WoW computation."""
    if len(rows) == 1:
        return rows[0], None

    # Sort by date_range if available; otherwise use positional order
    def _date_key(r: CampaignMetrics) -> str:
        return r.date_range or ""

    sorted_rows = sorted(rows, key=_date_key)
    latest = sorted_rows[-1]
    prior = sorted_rows[-2]
    return latest, prior
