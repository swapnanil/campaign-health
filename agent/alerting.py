from __future__ import annotations

from typing import Literal

from .models import AlertReport, AlertRule, AlertTrigger, CampaignMetrics

DEFAULT_ALERT_RULES: list[AlertRule] = [
    AlertRule(metric="cpa", condition="gt", threshold=500, severity="critical", label="CPA Critical"),
    AlertRule(metric="roas", condition="lt", threshold=1.0, severity="critical", label="ROAS Critical"),
    AlertRule(metric="win_rate", condition="lt", threshold=10.0, severity="critical", label="Win Rate Critical"),
    AlertRule(metric="win_rate", condition="lt", threshold=20.0, severity="warning", label="Win Rate Warning"),
    AlertRule(metric="frequency", condition="gt", threshold=7.0, severity="warning", label="Frequency Fatigue"),
    AlertRule(metric="budget_utilisation", condition="lt", threshold=70.0, severity="warning", label="Budget Under-pacing"),
    AlertRule(metric="viewability", condition="lt", threshold=30.0, severity="warning", label="Low Viewability"),
    AlertRule(metric="ctr", condition="lt", threshold=0.05, severity="warning", label="CTR Critically Low"),
]

_SEVERITY_RANK: dict[str, int] = {"critical": 3, "warning": 2, "info": 1}


def _check_condition(value: float, condition: str, threshold: float) -> bool:
    if condition == "gt":
        return value > threshold
    if condition == "gte":
        return value >= threshold
    if condition == "lt":
        return value < threshold
    if condition == "lte":
        return value <= threshold
    return False


def _highest_severity(triggers: list[AlertTrigger]) -> Literal["critical", "warning", "info", "none"]:
    if not triggers:
        return "none"
    return max(triggers, key=lambda t: _SEVERITY_RANK.get(t.severity, 0)).severity  # type: ignore[return-value]


def evaluate_alerts(
    metrics: CampaignMetrics,
    rules: list[AlertRule] | None = None,
) -> AlertReport:
    active_rules = rules if rules is not None else DEFAULT_ALERT_RULES

    triggers: list[AlertTrigger] = []
    for rule in active_rules:
        value = getattr(metrics, rule.metric, None)
        if value is None:
            continue
        if not isinstance(value, (int, float)):
            continue
        if _check_condition(float(value), rule.condition, rule.threshold):
            triggers.append(AlertTrigger(
                rule_label=rule.label,
                metric=rule.metric,
                observed_value=float(value),
                threshold=rule.threshold,
                condition=rule.condition,
                severity=rule.severity,
                message=(
                    f"{rule.label}: {rule.metric} is {value} "
                    f"({rule.condition} threshold {rule.threshold})"
                ),
            ))

    highest = _highest_severity(triggers)

    if not triggers:
        summary = f"No alerts triggered for campaign {metrics.campaign_id}."
    elif highest == "critical":
        critical_labels = [t.rule_label for t in triggers if t.severity == "critical"]
        summary = (
            f"{len(triggers)} alert(s) for {metrics.campaign_id}. "
            f"CRITICAL: {', '.join(critical_labels)}."
        )
    else:
        summary = (
            f"{len(triggers)} alert(s) for {metrics.campaign_id}. "
            f"Highest severity: {highest}."
        )

    return AlertReport(
        campaign_id=metrics.campaign_id,
        triggers=triggers,
        total_alerts=len(triggers),
        highest_severity=highest,
        alert_summary=summary,
    )
