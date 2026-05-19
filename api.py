from __future__ import annotations

import io
import logging
import os
from typing import Annotated

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.responses import JSONResponse

load_dotenv()

from agent.alerting import DEFAULT_ALERT_RULES, evaluate_alerts
from agent.benchmarks import get_vertical_benchmarks, list_verticals
from agent.diagnostician import compare_campaigns, diagnose_batch, diagnose_campaign
from agent.digest import generate_weekly_digest
from agent.models import (
    AlertReport,
    AlertRule,
    BatchDiagnosis,
    BenchmarkResponse,
    CampaignComparison,
    CampaignDiagnosis,
    CampaignMetrics,
    HealthResponse,
    PacingProjection,
    PrioritisedDiagnosis,
    VerticalBenchmarks,
    WeeklyDigest,
)
from agent.pacing import project_budget_pacing
from agent.preprocessor import load_csv, validate_metrics
from agent.prioritiser import prioritise_recommendations

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Campaign Health Diagnostician",
    description="Expert AI diagnosis of ad campaign performance metrics.",
    version="1.0.0",
)

MODEL = os.getenv("MODEL", "claude-sonnet-4-6")

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL)


@app.get("/benchmarks", response_model=BenchmarkResponse, tags=["System"])
async def benchmarks() -> BenchmarkResponse:
    return BenchmarkResponse(
        ctr_benchmark_display_pct=float(os.getenv("CTR_BENCHMARK_DISPLAY", "0.1")),
        ctr_benchmark_search_pct=float(os.getenv("CTR_BENCHMARK_SEARCH", "2.0")),
        win_rate_concern_threshold_pct=20.0,
        win_rate_critical_threshold_pct=10.0,
        frequency_fatigue_threshold=7.0,
        cpa_spike_threshold_pct=40.0,
        budget_underpacing_threshold_pct=70.0,
        roas_critical_threshold=1.0,
    )


@app.post("/diagnose", response_model=CampaignDiagnosis, tags=["Diagnosis"])
async def diagnose_single(metrics: CampaignMetrics) -> CampaignDiagnosis:
    errors = validate_metrics(metrics)
    if errors:
        raise HTTPException(status_code=422, detail={"data_quality_errors": errors})

    try:
        return diagnose_campaign(metrics, client=get_client())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/diagnose/csv", tags=["Diagnosis"])
async def diagnose_csv(file: Annotated[UploadFile, File(description="CSV file with campaign metrics")]):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    contents = await file.read()

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        records = load_csv(tmp_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        import os as _os
        _os.unlink(tmp_path)

    unique_campaigns = len(set(r.campaign_id for r in records))

    try:
        if unique_campaigns > 1:
            result = diagnose_batch(records, client=get_client())
        else:
            from agent.preprocessor import aggregate_campaign
            latest, prior = aggregate_campaign(records)
            result = diagnose_campaign(latest, client=get_client(), prior_period=prior)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return JSONResponse(content=result.model_dump())


@app.post("/diagnose/batch", response_model=BatchDiagnosis, tags=["Diagnosis"])
async def diagnose_batch_endpoint(campaigns: list[CampaignMetrics]) -> BatchDiagnosis:
    if not campaigns:
        raise HTTPException(status_code=422, detail="campaigns list cannot be empty.")

    for m in campaigns:
        errors = validate_metrics(m)
        if errors:
            raise HTTPException(
                status_code=422,
                detail={"campaign_id": m.campaign_id, "data_quality_errors": errors},
            )

    try:
        return diagnose_batch(campaigns, client=get_client())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


class AlertEvalRequest(BaseModel):
    metrics: CampaignMetrics
    rules: list[AlertRule] | None = None


@app.post("/alerts/evaluate", response_model=AlertReport, tags=["Alerts"])
async def evaluate_alerts_endpoint(req: AlertEvalRequest) -> AlertReport:
    return evaluate_alerts(req.metrics, req.rules)


@app.get("/alerts/rules", tags=["Alerts"])
async def get_default_rules() -> list[AlertRule]:
    return DEFAULT_ALERT_RULES


class PacingRequest(BaseModel):
    campaign_id: str
    current_spend: float
    total_budget: float
    period_hours: float
    elapsed_hours: float


@app.post("/pacing", response_model=PacingProjection, tags=["Pacing"])
async def pacing_endpoint(req: PacingRequest) -> PacingProjection:
    try:
        return project_budget_pacing(
            req.campaign_id, req.current_spend, req.total_budget,
            req.period_hours, req.elapsed_hours,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/benchmarks/verticals", tags=["Benchmarks"])
async def list_verticals_endpoint() -> dict:
    return {"verticals": list_verticals()}


@app.get("/benchmarks/{vertical}", response_model=VerticalBenchmarks, tags=["Benchmarks"])
async def get_vertical_endpoint(vertical: str) -> VerticalBenchmarks:
    return get_vertical_benchmarks(vertical)


@app.post("/diagnose/prioritise", response_model=PrioritisedDiagnosis, tags=["Diagnosis"])
async def prioritise_endpoint(diagnosis: CampaignDiagnosis) -> PrioritisedDiagnosis:
    return prioritise_recommendations(diagnosis)


@app.post("/diagnose/compare", response_model=CampaignComparison, tags=["Diagnosis"])
async def compare_endpoint(campaigns: list[CampaignMetrics]) -> CampaignComparison:
    if len(campaigns) != 2:
        raise HTTPException(status_code=422, detail="Exactly 2 campaigns required for comparison.")
    try:
        return compare_campaigns(campaigns[0], campaigns[1], client=get_client())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/digest", response_model=WeeklyDigest, tags=["Digest"])
async def digest_endpoint(
    diagnoses: list[CampaignDiagnosis],
    week_label: str | None = None,
) -> WeeklyDigest:
    if not diagnoses:
        raise HTTPException(status_code=422, detail="At least one diagnosis is required.")
    try:
        return generate_weekly_digest(diagnoses, week_label=week_label, client=get_client())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
