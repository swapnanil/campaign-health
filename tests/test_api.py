from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _make_diagnosis_dict(campaign_id: str = "test", health: str = "healthy") -> dict:
    return {
        "campaign_id": campaign_id,
        "campaign_name": None,
        "overall_health": health,
        "health_score": 85,
        "executive_summary": "Test summary.",
        "issues": [],
        "top_3_actions": ["Action 1"],
        "positive_signals": ["Signal 1"],
    }


def _make_batch_dict(campaign_ids: list[str]) -> dict:
    return {
        "campaigns": [_make_diagnosis_dict(cid) for cid in campaign_ids],
        "fleet_summary": "Fleet looks fine.",
    }


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


@pytest.fixture
def mock_diagnose_campaign():
    from agent.models import CampaignDiagnosis

    def _mock(metrics, **kwargs):
        return CampaignDiagnosis(**_make_diagnosis_dict(metrics.campaign_id))

    with patch("api.diagnose_campaign", side_effect=_mock) as m:
        yield m


@pytest.fixture
def mock_diagnose_batch():
    from agent.models import BatchDiagnosis

    def _mock(campaigns, **kwargs):
        return BatchDiagnosis(**_make_batch_dict([c.campaign_id for c in campaigns]))

    with patch("api.diagnose_batch", side_effect=_mock) as m:
        yield m


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "model" in data

    def test_health_model_is_claude(self, client):
        response = client.get("/health")
        assert "claude" in response.json()["model"].lower()


class TestBenchmarksEndpoint:
    def test_benchmarks_returns_thresholds(self, client):
        response = client.get("/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert "ctr_benchmark_display_pct" in data
        assert "win_rate_critical_threshold_pct" in data
        assert data["roas_critical_threshold"] == 1.0


class TestDiagnoseSingleEndpoint:
    def test_valid_metrics_returns_diagnosis(self, client, mock_diagnose_campaign):
        payload = {
            "campaign_id": "camp_003",
            "spend": 36000,
            "ctr": 3.2,
            "win_rate": 42,
            "roas": 2.8,
            "frequency": 3.0,
        }
        response = client.post("/diagnose", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["campaign_id"] == "camp_003"
        assert data["overall_health"] in ("healthy", "degraded", "critical")

    def test_missing_spend_returns_422(self, client):
        response = client.post("/diagnose", json={"campaign_id": "x"})
        assert response.status_code == 422

    def test_all_zero_metrics_returns_422(self, client):
        payload = {"campaign_id": "x", "spend": 0, "impressions": 0, "clicks": 0}
        response = client.post("/diagnose", json=payload)
        assert response.status_code == 422

    def test_negative_roas_allowed_but_flagged(self, client, mock_diagnose_campaign):
        payload = {"campaign_id": "x", "spend": 5000, "roas": 0.5}
        response = client.post("/diagnose", json=payload)
        assert response.status_code == 200


class TestDiagnoseCsvEndpoint:
    def test_good_csv_returns_diagnosis(self, client, mock_diagnose_campaign):
        csv_path = EXAMPLES_DIR / "sample_campaign_good.csv"
        with open(csv_path, "rb") as f:
            response = client.post("/diagnose/csv", files={"file": ("sample.csv", f, "text/csv")})
        assert response.status_code == 200
        data = response.json()
        assert "campaign_id" in data or "campaigns" in data

    def test_cpa_spike_csv_returns_diagnosis(self, client, mock_diagnose_campaign):
        csv_path = EXAMPLES_DIR / "sample_campaign_cpa_spike.csv"
        with open(csv_path, "rb") as f:
            response = client.post("/diagnose/csv", files={"file": ("sample.csv", f, "text/csv")})
        assert response.status_code == 200

    def test_non_csv_file_rejected(self, client):
        response = client.post(
            "/diagnose/csv",
            files={"file": ("data.txt", b"not a csv", "text/plain")},
        )
        assert response.status_code == 400

    def test_csv_missing_required_column_returns_422(self, client, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("campaign_id,impressions\nc1,10000\n")
        with open(bad_csv, "rb") as f:
            response = client.post("/diagnose/csv", files={"file": ("bad.csv", f, "text/csv")})
        assert response.status_code == 422


class TestDiagnoseBatchEndpoint:
    def test_batch_endpoint_returns_batch_diagnosis(self, client, mock_diagnose_batch):
        payload = [
            {"campaign_id": "c1", "spend": 10000, "win_rate": 30},
            {"campaign_id": "c2", "spend": 20000, "ctr": 1.2},
        ]
        response = client.post("/diagnose/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "campaigns" in data
        assert "fleet_summary" in data
        assert len(data["campaigns"]) == 2

    def test_empty_batch_returns_422(self, client):
        response = client.post("/diagnose/batch", json=[])
        assert response.status_code == 422

    def test_batch_with_invalid_campaign_returns_422(self, client):
        payload = [
            {"campaign_id": "x", "spend": 0, "impressions": 0, "clicks": 0},
        ]
        response = client.post("/diagnose/batch", json=payload)
        assert response.status_code == 422
