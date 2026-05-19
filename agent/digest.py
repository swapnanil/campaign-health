from __future__ import annotations

import os
from collections import Counter

import anthropic

from .models import CampaignDiagnosis, CampaignSummary, WeeklyDigest
from .prompts import build_digest_prompt

MODEL = os.getenv("MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "512"))


def _call_llm(prompt: str, client: anthropic.Anthropic) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip().strip('"')


def generate_weekly_digest(
    diagnoses: list[CampaignDiagnosis],
    week_label: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> WeeklyDigest:
    if not diagnoses:
        raise ValueError("At least one diagnosis is required to generate a digest.")

    healthy = sum(1 for d in diagnoses if d.overall_health == "healthy")
    degraded = sum(1 for d in diagnoses if d.overall_health == "degraded")
    critical = sum(1 for d in diagnoses if d.overall_health == "critical")
    avg_score = sum(d.health_score for d in diagnoses) / len(diagnoses)

    issue_counter: Counter[str] = Counter()
    for d in diagnoses:
        for issue in d.issues:
            issue_counter[issue.metric] += 1
    most_common = [metric for metric, _ in issue_counter.most_common(5)]

    critical_ids = [d.campaign_id for d in diagnoses if d.overall_health == "critical"]

    summaries = [
        CampaignSummary(
            campaign_id=d.campaign_id,
            campaign_name=d.campaign_name,
            overall_health=d.overall_health,
            health_score=d.health_score,
            top_issue=d.issues[0].metric if d.issues else None,
        )
        for d in diagnoses
    ]

    if client is None:
        client = anthropic.Anthropic()

    digest_prompt = build_digest_prompt(
        total=len(diagnoses),
        healthy=healthy,
        degraded=degraded,
        critical=critical,
        most_common_issues=most_common,
        critical_campaign_ids=critical_ids,
    )
    digest_summary = _call_llm(digest_prompt, client)

    return WeeklyDigest(
        week_label=week_label,
        total_campaigns=len(diagnoses),
        healthy=healthy,
        degraded=degraded,
        critical=critical,
        fleet_average_score=round(avg_score, 1),
        most_common_issues=most_common,
        campaign_summaries=summaries,
        digest_summary=digest_summary,
    )
