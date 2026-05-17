# campaign-health
> Paste your campaign metrics. Get expert diagnosis — root causes, severity, and exactly what to fix first.

Part of the [llm-tools suite](https://github.com/swapnanil) by [Swapnanil Saha](https://swapnanilsaha.com)

## What it does

When CPA spikes, most teams raise or lower bids and hope. Campaign Health pre-processes your metrics — computing week-on-week trends, detecting anomalies, and flagging benchmark deltas — then uses Claude to deliver a diagnosis with root causes ordered by severity and a prioritised action list. Not symptoms. Causes.

## Quick start

```bash
git clone https://github.com/swapnanil/campaign-health
cd campaign-health
cp .env.example .env   # add your ANTHROPIC_API_KEY
docker-compose up api
```

## CLI usage

```bash
# Diagnose a single campaign CSV
docker-compose run cli diagnose \
  --file examples/sample_campaign_cpa_spike.csv \
  --format markdown

# Batch diagnose a campaign fleet
docker-compose run cli batch \
  --file examples/campaign_fleet.csv \
  --format json --output reports/

# Diagnose from JSON
docker-compose run cli diagnose \
  --file examples/campaign_metrics.json \
  --format json
```

## API usage

```bash
# Diagnose a campaign
curl -X POST http://localhost:8000/diagnose \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "CAMP_001", "impressions": 1200000, "clicks": 1440, "spend": 14280, "ctr": 0.12, "cpa": 420, "win_rate": 35, "frequency": 9}'

# Upload a CSV for batch diagnosis
curl -X POST http://localhost:8000/diagnose/csv \
  -F "file=@examples/campaign_fleet.csv"
```

## Input / Output

**Input (CSV row):**
```
campaign_id,impressions,clicks,spend,ctr,cpa,win_rate,frequency
CAMP_001,1200000,1440,14280,0.12,420,35,9
```
*(CPA was ₹250 in weeks 1–2)*

**Output excerpt:**
```json
{
  "health_score": 31,
  "overall_health": "critical",
  "issues": [
    {
      "severity": "critical",
      "metric": "cpa",
      "value": 420,
      "change": "+68% WoW",
      "root_cause": "Frequency at 9 = audience exhaustion, not a bid problem",
      "recommendation": "Add frequency cap of 4, expand lookalike audience"
    }
  ],
  "top_action": "Pause creative and launch 2 new variants before increasing spend"
}
```

## Built with

- Python 3.11
- Anthropic SDK (claude-sonnet-4-6)
- FastAPI + uvicorn
- Docker + docker-compose
- pytest

## Author

Swapnanil Saha · [swapnanilsaha.com](https://swapnanilsaha.com) · [LinkedIn](https://linkedin.com/in/swapnanil)
