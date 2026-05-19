from __future__ import annotations

from typing import Literal

from .models import CampaignDiagnosis, Issue, PrioritisedDiagnosis, PrioritisedIssue

_HIGH_EFFORT_KEYWORDS = {
    "creative", "landing page", "tracking", "restructure", "rebuild",
    "audience rebuild", "pixel", "attribution",
}
_LOW_EFFORT_KEYWORDS = {
    "bid", "budget", "frequency cap", "cap", "pacing", "daypart",
    "spend cap", "floor", "increase bids", "reduce bids",
}

_SEVERITY_BASE: dict[str, int] = {"critical": 85, "warning": 55, "info": 25}
_HIGH_IMPACT_METRICS = {"cpa", "roas", "win_rate", "ctr"}


def _classify_effort(issue: Issue) -> Literal["low", "medium", "high"]:
    text = (issue.root_cause + " " + issue.recommendation).lower()
    for kw in _HIGH_EFFORT_KEYWORDS:
        if kw in text:
            return "high"
    for kw in _LOW_EFFORT_KEYWORDS:
        if kw in text:
            return "low"
    return "medium"


def _compute_priority_score(issue: Issue) -> int:
    base = _SEVERITY_BASE.get(issue.severity, 25)
    boost = 0
    if issue.metric.lower() in _HIGH_IMPACT_METRICS:
        boost += 10
    if "spike" in issue.root_cause.lower():
        boost += 5
    return min(100, base + boost)


def prioritise_recommendations(diagnosis: CampaignDiagnosis) -> PrioritisedDiagnosis:
    prioritised: list[PrioritisedIssue] = []

    for issue in diagnosis.issues:
        effort = _classify_effort(issue)
        score = _compute_priority_score(issue)
        prioritised.append(PrioritisedIssue(
            metric=issue.metric,
            severity=issue.severity,
            root_cause=issue.root_cause,
            recommendation=issue.recommendation,
            estimated_impact=issue.estimated_impact,
            effort=effort,
            priority_score=score,
        ))

    prioritised.sort(key=lambda x: x.priority_score, reverse=True)

    quick_wins = [
        p.recommendation
        for p in prioritised
        if p.effort == "low" and p.priority_score >= 70
    ]

    return PrioritisedDiagnosis(
        campaign_id=diagnosis.campaign_id,
        overall_health=diagnosis.overall_health,
        health_score=diagnosis.health_score,
        prioritised_issues=prioritised,
        quick_wins=quick_wins,
    )
