from __future__ import annotations

import json

from agent.models import PreprocessedMetrics

SYSTEM_PROMPT = """You are a senior ad-tech engineer with 9 years of experience in real-time bidding,
programmatic advertising, and campaign optimisation across display, search, and native formats.

You are diagnosing ad campaign performance data the way a doctor reads a patient's vitals —
looking for patterns, anomalies, and root causes, not just surface-level observations.

Your diagnosis must be:
- Specific: name the exact metric, the exact value, and the exact problem
- Causal: explain WHY the metric is behaving this way, not just THAT it is
- Actionable: give recommendations that an ad ops team can execute today
- Prioritised: order issues by business impact, not metric order
- Honest: if the data looks healthy, say so. Don't invent problems.

Domain knowledge to apply:
- CTR below 0.05% on display = creative or audience problem, not bid problem
- Win rate below 15% = underbidding or floor price issue
- CPA spike > 40% WoW without volume change = conversion tracking issue or audience saturation
- Budget utilisation below 70% by midday = pacing algorithm or bid too conservative
- High frequency (>8) + dropping CTR = classic ad fatigue
- ROAS below 1.0 = campaign is destroying value, flag as critical regardless of other metrics

Respond ONLY with valid JSON matching the schema. No preamble, no markdown fences."""

SCHEMA_REMINDER = """
The JSON must conform exactly to this schema:
{
  "campaign_id": "string",
  "campaign_name": "string or null",
  "overall_health": "healthy" | "degraded" | "critical",
  "health_score": integer 0-100,
  "executive_summary": "2-3 sentences",
  "issues": [
    {
      "metric": "string",
      "observed_value": "string",
      "expected_range": "string",
      "severity": "critical" | "warning" | "info",
      "root_cause": "string",
      "recommendation": "string",
      "estimated_impact": "string"
    }
  ],
  "top_3_actions": ["string", "string", "string"],
  "positive_signals": ["string"]
}
Respond with valid JSON only. No markdown fences, no preamble.
"""


def build_user_prompt(metrics: PreprocessedMetrics, currency: str = "INR") -> str:
    def _fmt(v: float | None, unit: str = "") -> str:
        if v is None:
            return "N/A"
        return f"{v}{unit}"

    lines = [
        f"Campaign ID: {metrics.campaign_id}",
        f"Campaign Name: {metrics.campaign_name or 'N/A'}",
        f"Date Range: {metrics.date_range or 'N/A'}",
        "",
        "=== RAW METRICS ===",
        f"Impressions: {_fmt(metrics.impressions)}",
        f"Clicks: {_fmt(metrics.clicks)}",
        f"Conversions: {_fmt(metrics.conversions)}",
        f"Spend: {currency} {metrics.spend}",
        f"CTR: {_fmt(metrics.ctr, '%')}",
        f"CPC: {currency} {_fmt(metrics.cpc)}",
        f"CPA: {currency} {_fmt(metrics.cpa)}",
        f"CVR: {_fmt(metrics.cvr, '%')}",
        f"Win Rate: {_fmt(metrics.win_rate, '%')}",
        f"Avg Bid: {currency} {_fmt(metrics.avg_bid)}",
        f"Floor Price: {currency} {_fmt(metrics.floor_price)}",
        f"ROAS: {_fmt(metrics.roas)}",
        f"Viewability: {_fmt(metrics.viewability, '%')}",
        f"Frequency: {_fmt(metrics.frequency)}",
        f"Budget Utilisation: {_fmt(metrics.budget_utilisation, '%')}",
        "",
        "=== COMPUTED / DERIVED METRICS ===",
        f"CTR (computed): {_fmt(metrics.ctr_computed, '%')}",
        f"CPC (computed): {currency} {_fmt(metrics.cpc_computed)}",
        f"CPA (computed): {currency} {_fmt(metrics.cpa_computed)}",
        f"CVR (computed): {_fmt(metrics.cvr_computed, '%')}",
        "",
        "=== WEEK-OVER-WEEK CHANGES ===",
        f"CPA WoW Change: {_fmt(metrics.cpa_wow_change, '%')}",
        f"CTR WoW Change: {_fmt(metrics.ctr_wow_change, '%')}",
        f"Spend WoW Change: {_fmt(metrics.spend_wow_change, '%')}",
        "",
        "=== ANOMALY FLAGS ===",
        f"CTR below benchmark ({metrics.ctr_benchmark}%): {metrics.ctr_below_benchmark}",
        f"Win Rate CRITICAL (below 10%): {metrics.win_rate_critical}",
        f"Win Rate CONCERN (below 20%): {metrics.win_rate_concern}",
        f"CPA Spike (>40% WoW): {metrics.cpa_spike}",
        f"Budget Under-pacing (<70%): {metrics.budget_underpacing}",
        f"Frequency Fatigue (>7): {metrics.frequency_fatigue}",
        f"ROAS Critical (<1.0): {metrics.roas_critical}",
        f"Bid Below Floor Price: {metrics.bid_below_floor}",
        "",
        "=== BENCHMARK DELTAS ===",
        f"CTR vs benchmark: {_fmt(metrics.ctr_delta_pct, '%')}",
        f"Win Rate vs healthy threshold: {_fmt(metrics.win_rate_delta_pct, '%')}",
        f"Pacing Status: {metrics.pacing_status}",
    ]

    if metrics.cpa_target:
        lines.append(f"CPA Target: {currency} {metrics.cpa_target}")

    lines += [
        "",
        "Based on this data, provide your expert diagnosis as valid JSON matching the schema.",
    ]

    return "\n".join(lines)


def build_batch_fleet_prompt(campaign_ids: list[str]) -> str:
    return (
        f"You have diagnosed {len(campaign_ids)} campaigns: {', '.join(campaign_ids)}. "
        "Write a concise fleet_summary (2-4 sentences) identifying cross-campaign patterns, "
        "systemic issues, or portfolio-level observations. Be specific about which campaigns share issues."
    )


def schema_correction_prompt(bad_json: str) -> str:
    return (
        f"Your previous response was not valid JSON or did not match the required schema.\n"
        f"Previous response:\n{bad_json[:500]}\n\n"
        + SCHEMA_REMINDER
    )
