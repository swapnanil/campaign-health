# campaign-health
> Paste your campaign metrics. Get expert diagnosis — root causes, severity, and exactly what to fix first.

Part of the [llm-tools suite](https://github.com/swapnanil) by [Swapnanil Saha](https://swapnanilsaha.com)

## What it does

When CPA spikes, most teams raise or lower bids and hope. Campaign Health pre-processes your metrics — computing week-on-week trends, detecting anomalies, and flagging benchmark deltas — then uses Claude to deliver a diagnosis with root causes ordered by severity and a prioritised action list. Not symptoms. Causes.

v2 adds six operational features that turn a diagnostic tool into a campaign ops platform: custom alert rules, budget pacing projection, vertical-specific benchmarks, recommendation prioritisation, weekly digest reports for clients, and head-to-head campaign comparison.

## Features

| Feature | Description |
|---|---|
| Expert diagnosis | Claude diagnoses root causes with evidence, ordered by business impact |
| WoW trend detection | Week-on-week CPA, CTR, and spend changes computed automatically |
| Alert Rules Engine | Custom threshold rules trigger structured alerts per campaign |
| Budget Pacing Projection | Burn-rate model projects spend to end of period; flags burnout risk |
| Vertical Benchmarks | Industry-specific benchmarks for ecomm, fintech, gaming, travel, healthcare |
| Recommendation Prioritiser | Sorts issues by effort vs. impact; extracts quick wins |
| Weekly Digest | Client-facing fleet summary with most common issues and LLM narrative |
| Campaign Comparison | Head-to-head analysis of two campaigns with metric deltas |
| Batch fleet diagnosis | Diagnose an entire campaign fleet from a single CSV |
| JUnit-compatible | Health scores can be gated in CI against configurable thresholds |

## Quick start

```bash
git clone https://github.com/swapnanil/campaign-health
cd campaign-health
cp .env.example .env   # add your ANTHROPIC_API_KEY
docker-compose up api
```

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/diagnose` | Diagnose a single campaign |
| POST | `/diagnose/csv` | Upload CSV for single or batch diagnosis |
| POST | `/diagnose/batch` | Batch diagnose a list of campaigns |
| POST | `/diagnose/prioritise` | Sort a diagnosis's issues by effort and impact |
| POST | `/diagnose/compare` | Compare two campaigns head-to-head |
| POST | `/alerts/evaluate` | Evaluate custom alert rules against campaign metrics |
| GET | `/alerts/rules` | List default alert rules |
| POST | `/pacing` | Project budget spend to end of period |
| GET | `/benchmarks/verticals` | List available industry verticals |
| GET | `/benchmarks/{vertical}` | Get benchmark thresholds for a vertical |
| POST | `/digest` | Generate a weekly fleet digest |
| GET | `/benchmarks` | Default benchmark thresholds |

## CLI usage

```bash
# Diagnose a single campaign
docker-compose run cli diagnose \
  --file examples/sample_campaign_cpa_spike.csv \
  --format markdown

# Batch diagnose a fleet
docker-compose run cli batch \
  --file examples/campaign_fleet.csv --format json

# Check budget pacing
docker-compose run cli pacing \
  --campaign-id CAMP_001 --spend 8000 --budget 10000 \
  --period-hours 24 --elapsed-hours 6

# Generate weekly digest
docker-compose run cli digest diagnoses.json --week 2026-W20
```

## Alert Rules Engine

```json
{
  "metrics": {"campaign_id": "CAMP_001", "spend": 14280, "cpa": 620, "roas": 0.9, "win_rate": 8},
  "rules": [
    {"metric": "cpa", "condition": "gt", "threshold": 500, "severity": "critical", "label": "CPA Critical"},
    {"metric": "roas", "condition": "lt", "threshold": 1.0, "severity": "critical", "label": "ROAS Critical"}
  ]
}
```

**Output:**
```json
{
  "total_alerts": 2,
  "highest_severity": "critical",
  "alert_summary": "2 alert(s) for CAMP_001. CRITICAL: CPA Critical, ROAS Critical.",
  "triggers": [...]
}
```

## Vertical Benchmarks

```bash
curl http://localhost:8000/benchmarks/gaming
```
```json
{
  "vertical": "gaming",
  "ctr_display_pct": 0.20,
  "ctr_search_pct": 1.8,
  "win_rate_healthy_pct": 35.0,
  "roas_target": 2.0,
  "frequency_fatigue_threshold": 10.0
}
```

Supported verticals: `ecomm`, `fintech`, `gaming`, `travel`, `healthcare`, `general`

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Anthropic API key |
| `MODEL` | `claude-sonnet-4-6` | LLM model for diagnosis |
| `MAX_TOKENS` | `2048` | Max tokens per diagnosis call |
| `DEFAULT_CURRENCY` | `INR` | Currency label in prompts |
| `CTR_BENCHMARK_DISPLAY` | `0.1` | Default display CTR benchmark (%) |
| `CTR_BENCHMARK_SEARCH` | `2.0` | Default search CTR benchmark (%) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Built with

- Python 3.11
- Anthropic SDK (`claude-sonnet-4-6`)
- FastAPI + uvicorn
- Docker + docker-compose
- pytest (121 tests)

## Author

Swapnanil Saha · [swapnanilsaha.com](https://swapnanilsaha.com) · [LinkedIn](https://linkedin.com/in/swapnanil)
