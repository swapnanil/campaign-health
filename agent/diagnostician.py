from __future__ import annotations

import json
import logging
import os
import time

import anthropic

from agent.models import BatchDiagnosis, CampaignDiagnosis, CampaignMetrics, PreprocessedMetrics
from agent.preprocessor import aggregate_campaign, group_by_campaign, preprocess, validate_metrics
from agent.prompts import (
    SYSTEM_PROMPT,
    build_batch_fleet_prompt,
    build_user_prompt,
    schema_correction_prompt,
)

logger = logging.getLogger(__name__)

MODEL = os.getenv("MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


def _call_claude(
    client: anthropic.Anthropic,
    user_content: str,
    system: str = SYSTEM_PROMPT,
) -> str:
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
            return response.content[0].text
        except anthropic.RateLimitError as e:
            last_error = e
            delay = RETRY_BASE_DELAY * (2**attempt)
            logger.warning("Rate limited. Retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, MAX_RETRIES)
            time.sleep(delay)
        except anthropic.APIError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning("API error: %s. Retrying in %.1fs", e, delay)
                time.sleep(delay)

    raise RuntimeError(f"Claude API call failed after {MAX_RETRIES} attempts: {last_error}")


def _parse_diagnosis(raw: str, campaign_id: str) -> CampaignDiagnosis:
    try:
        data = json.loads(raw)
        return CampaignDiagnosis(**data)
    except (json.JSONDecodeError, Exception):
        raise ValueError(f"Invalid JSON from LLM for campaign {campaign_id}: {raw[:200]}")


def diagnose_campaign(
    metrics: CampaignMetrics,
    client: anthropic.Anthropic | None = None,
    ctr_benchmark: float | None = None,
    cpa_target: float | None = None,
    prior_period: CampaignMetrics | None = None,
) -> CampaignDiagnosis:
    if client is None:
        client = anthropic.Anthropic()

    errors = validate_metrics(metrics)
    if errors:
        raise ValueError(f"Data quality issues for campaign {metrics.campaign_id}: {'; '.join(errors)}")

    effective_ctr_benchmark = ctr_benchmark or float(os.getenv("CTR_BENCHMARK_DISPLAY", "0.1"))

    preprocessed = preprocess(
        metrics,
        ctr_benchmark=effective_ctr_benchmark,
        cpa_target=cpa_target,
        prior_period=prior_period,
    )

    user_prompt = build_user_prompt(preprocessed, currency=CURRENCY)

    raw = _call_claude(client, user_prompt)

    try:
        return _parse_diagnosis(raw, metrics.campaign_id)
    except ValueError:
        logger.warning("LLM returned invalid JSON for %s — retrying with schema correction.", metrics.campaign_id)
        correction_prompt = user_prompt + "\n\n" + schema_correction_prompt(raw)
        raw2 = _call_claude(client, correction_prompt)
        return _parse_diagnosis(raw2, metrics.campaign_id)


def diagnose_batch(
    campaigns: list[CampaignMetrics],
    client: anthropic.Anthropic | None = None,
    ctr_benchmark: float | None = None,
    cpa_target: float | None = None,
) -> BatchDiagnosis:
    if client is None:
        client = anthropic.Anthropic()

    grouped = group_by_campaign(campaigns)
    diagnoses: list[CampaignDiagnosis] = []

    for campaign_id, rows in grouped.items():
        latest, prior = aggregate_campaign(rows)
        diagnosis = diagnose_campaign(
            latest,
            client=client,
            ctr_benchmark=ctr_benchmark,
            cpa_target=cpa_target,
            prior_period=prior,
        )
        diagnoses.append(diagnosis)

    fleet_prompt = build_batch_fleet_prompt([d.campaign_id for d in diagnoses])
    fleet_summary_raw = _call_claude(client, fleet_prompt, system=SYSTEM_PROMPT)
    fleet_summary = fleet_summary_raw.strip().strip('"')

    return BatchDiagnosis(campaigns=diagnoses, fleet_summary=fleet_summary)
