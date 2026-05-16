# Campaign Health Diagnostician

**llm-tools suite by [Swapnanil Saha](https://swapnanilsaha.com)**

---

## What This Does

Ad operations teams and performance marketers spend hours manually interpreting campaign dashboards. Metrics like CTR, CPA, win rate, and impression share interact in non-obvious ways — a low CTR might mean creative failure, audience mismatch, or placement quality issues depending on what the other metrics say.

This tool ingests raw ad campaign performance data and returns an expert diagnosis: what is broken, why it is broken, how severe it is, and exactly what to fix — in priority order. It simulates what a senior ad-tech engineer with 9 years of RTB experience would tell you in 30 seconds of looking at your campaign data.

---

## Metrics Understood

| Metric | Description |
|---|---|
| `impressions` | Total ad impressions served |
| `clicks` | Total clicks |
| `conversions` | Total conversion events |
| `spend` | Total spend (required) |
| `ctr` | Click-through rate (%) — computed if not provided |
| `cpc` | Cost per click — computed if not provided |
| `cpa` | Cost per acquisition — computed if not provided |
| `cvr` | Conversion rate (%) |
| `win_rate` | Bid wins / bid attempts (%) |
| `avg_bid` | Average bid submitted |
| `floor_price` | Auction floor price |
| `roas` | Return on ad spend |
| `viewability` | % impressions that were viewable |
| `frequency` | Avg impressions per unique user |
| `budget_utilisation` | Spend / budget (%) |
| `date_range` | Period label — enables week-over-week change detection |

**Derived automatically:**
- CTR vs industry benchmark (0.1% display, 2.0% search)
- CPA trend (week-over-week change when multiple date rows provided)
- Win rate health classification (critical / concern / healthy)
- Frequency fatigue detection (>7 = risk)
- Budget pacing status
- Bid vs floor price check

---

## Quick Start with Docker

```bash
# 1. Clone and configure
git clone <repo>
cd campaign-health
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 2. Run the API
docker-compose up api

# 3. Run a CLI diagnosis
docker-compose run --rm cli diagnose --file examples/sample_campaign_cpa_spike.csv
```

---

## CLI Usage

```bash
# Install dependencies locally
pip install -r requirements.txt

# Diagnose a single campaign from CSV
python main.py diagnose --file examples/sample_campaign_cpa_spike.csv

# Diagnose multiple campaigns in batch mode
python main.py diagnose --file examples/multi_campaign.csv --batch

# From inline JSON
python main.py diagnose --json '{"campaign_id": "c001", "spend": 50000, "cpa": 420, "win_rate": 35, "frequency": 9.2}'

# Output formats
python main.py diagnose --file data.csv --format markdown
python main.py diagnose --file data.csv --format json
python main.py diagnose --file data.csv --format html --output report.html

# Override thresholds for non-standard benchmarks
python main.py diagnose --file data.csv --ctr-benchmark 0.08 --cpa-target 250
```

---

## API Usage

### Start the server
```bash
uvicorn api:app --reload
# or
docker-compose up api
```

### Check health
```bash
curl http://localhost:8000/health
# {"status":"ok","model":"claude-sonnet-4-6"}
```

### Get benchmarks
```bash
curl http://localhost:8000/benchmarks
```

### Diagnose a single campaign
```bash
curl -X POST http://localhost:8000/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "camp_001",
    "campaign_name": "Display Retargeting Q1",
    "spend": 21840,
    "ctr": 0.10,
    "cpa": 420,
    "win_rate": 35,
    "frequency": 9.2,
    "roas": 1.38,
    "budget_utilisation": 95
  }'
```

### Diagnose from CSV upload
```bash
curl -X POST http://localhost:8000/diagnose/csv \
  -F "file=@examples/sample_campaign_cpa_spike.csv"
```

### Batch diagnosis
```bash
curl -X POST http://localhost:8000/diagnose/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"campaign_id": "c1", "spend": 10000, "ctr": 0.03, "win_rate": 12},
    {"campaign_id": "c2", "spend": 36000, "ctr": 3.2, "roas": 2.8}
  ]'
```

---

## CSV Format

Download sample CSVs from the [`examples/`](examples/) directory.

```csv
campaign_id,campaign_name,date_range,impressions,clicks,conversions,spend,ctr,cpc,cpa,cvr,win_rate,avg_bid,floor_price,roas,viewability,frequency,budget_utilisation
camp_001,My Campaign,2024-01-22 to 2024-01-28,870000,870,52,21840,0.10,25.10,420,,35,22,14,1.38,63,9.2,95
```

**Required:** `campaign_id`, `spend`

**Multi-period WoW detection:** include multiple rows with the same `campaign_id` and different `date_range` values — the tool automatically computes week-over-week changes.

---

## Input → Output Example

**Input (CPA spike scenario):**
```
campaign_id: camp_001
spend: ₹21,840 | cpa: ₹420 | ctr: 0.10% | win_rate: 35% | frequency: 9.2
Prior week: cpa: ₹250 | frequency: 6.9
```

**Output:**
```json
{
  "campaign_id": "camp_001",
  "overall_health": "critical",
  "health_score": 28,
  "executive_summary": "This display retargeting campaign has entered a critical ad fatigue spiral. Frequency reached 9.2 while CPA spiked 68% WoW from ₹250 to ₹420.",
  "issues": [
    {
      "metric": "CPA",
      "observed_value": "₹420 (↑68% WoW)",
      "expected_range": "₹200–₹280",
      "severity": "critical",
      "root_cause": "Audience saturation from excessive frequency — users have stopped converting.",
      "recommendation": "Apply frequency cap of 3/week. Refresh creative. Expand audience pool.",
      "estimated_impact": "25–40% CPA reduction within 7 days"
    }
  ],
  "top_3_actions": [
    "Set frequency cap to 3/week immediately",
    "Launch 3 new creative variants",
    "Expand retargeting audience with 30-day lookback window"
  ],
  "positive_signals": ["Win rate 35% is healthy — bidding is not the problem"]
}
```

See the full example output at [`examples/sample_output.json`](examples/sample_output.json).

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key (required) |
| `MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `MAX_TOKENS` | `2048` | Max tokens in LLM response |
| `CTR_BENCHMARK_DISPLAY` | `0.1` | Display CTR benchmark (%) |
| `CTR_BENCHMARK_SEARCH` | `2.0` | Search CTR benchmark (%) |
| `DEFAULT_CURRENCY` | `INR` | Currency symbol in reports |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Project Structure

```
campaign-health/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── main.py                   # CLI entry point (Typer)
├── api.py                    # FastAPI REST API
├── agent/
│   ├── diagnostician.py      # Core diagnosis logic + Anthropic SDK calls
│   ├── prompts.py            # System prompt + user prompt builder
│   ├── models.py             # Pydantic input/output models
│   └── preprocessor.py      # Metric normalisation + anomaly pre-check
├── examples/
│   ├── sample_campaign_good.csv
│   ├── sample_campaign_cpa_spike.csv
│   ├── sample_campaign_low_ctr.csv
│   └── sample_output.json
└── tests/
    ├── conftest.py
    ├── test_diagnostician.py
    ├── test_preprocessor.py
    └── test_api.py
```

---

Built by [Swapnanil Saha](https://swapnanilsaha.com) — Tool 2 of 5 in the llm-tools suite.
