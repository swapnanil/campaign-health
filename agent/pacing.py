from __future__ import annotations

from .models import PacingProjection

_ON_PACE_LOW = 0.85
_ON_PACE_HIGH = 1.15
_BURNOUT_THRESHOLD = 1.30


def project_budget_pacing(
    campaign_id: str,
    current_spend: float,
    total_budget: float,
    period_hours: float,
    elapsed_hours: float,
) -> PacingProjection:
    if total_budget <= 0:
        raise ValueError("total_budget must be positive.")
    if period_hours <= 0:
        raise ValueError("period_hours must be positive.")
    if elapsed_hours < 0:
        raise ValueError("elapsed_hours cannot be negative.")
    if elapsed_hours > period_hours:
        raise ValueError("elapsed_hours cannot exceed period_hours.")
    if current_spend < 0:
        raise ValueError("current_spend cannot be negative.")

    pct_budget_used = (current_spend / total_budget) * 100
    pct_period_elapsed = (elapsed_hours / period_hours) * 100

    if elapsed_hours == 0:
        projected_total = 0.0
        pace_ratio = 0.0
        hours_to_exhaustion = None
        status = "under_pacing"
        recommendation = "No spend recorded yet. Verify campaign is active and bids are competitive."
    else:
        burn_rate = current_spend / elapsed_hours
        remaining_hours = period_hours - elapsed_hours
        projected_total = round(current_spend + burn_rate * remaining_hours, 2)
        pace_ratio = projected_total / total_budget
        hours_to_exhaustion = round(total_budget / burn_rate, 1) if burn_rate > 0 else None

        if pace_ratio >= _BURNOUT_THRESHOLD:
            status = "burnout_risk"
            remaining_budget = total_budget - current_spend
            safe_hours = round(remaining_budget / burn_rate, 1) if burn_rate > 0 else None
            recommendation = (
                f"Budget will exhaust in ~{safe_hours}h at current burn rate. "
                "Apply a daily spend cap or reduce bids by 20–30% immediately."
            )
        elif pace_ratio > _ON_PACE_HIGH:
            status = "over_pacing"
            recommendation = (
                "Over-pacing by {:.0f}%. Reduce bids 10–15% or enable dayparting "
                "to distribute spend across the full period.".format((pace_ratio - 1) * 100)
            )
        elif pace_ratio < _ON_PACE_LOW:
            status = "under_pacing"
            recommendation = (
                "Under-pacing by {:.0f}%. Increase bids 10–15% or broaden "
                "targeting criteria to accelerate delivery.".format((1 - pace_ratio) * 100)
            )
        else:
            status = "on_pace"
            hours_to_exhaustion = None
            recommendation = "Pacing is healthy. Continue monitoring every 2–4 hours."

    return PacingProjection(
        campaign_id=campaign_id,
        current_spend=current_spend,
        total_budget=total_budget,
        pct_budget_used=round(pct_budget_used, 1),
        pct_period_elapsed=round(pct_period_elapsed, 1),
        projected_total_spend=projected_total,
        pacing_status=status,
        hours_to_exhaustion=hours_to_exhaustion if status in ("burnout_risk", "over_pacing") else None,
        recommendation=recommendation,
    )
