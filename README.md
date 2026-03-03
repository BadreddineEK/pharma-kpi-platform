# 💊 Pharma KPI Platform

> End-to-end data platform for pharmaceutical KPI monitoring — ETL pipeline, columnar storage, REST API, interactive dashboards and ML forecasting.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red?logo=streamlit)](https://streamlit.io)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.10-yellow)](https://duckdb.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://docker.com)
[![CI](https://github.com/BadreddineEK/pharma-kpi-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/BadreddineEK/pharma-kpi-platform/actions)

---

## 🎯 What is this?

A production-grade data platform that simulates a real pharma data team's stack:

- **Automated ETL pipeline** — ingests and transforms KPI data (trials, sales, production)
- **DuckDB columnar storage** — fast analytical queries, zero config
- **FastAPI backend** — REST API serving processed KPIs
- **Streamlit dashboard** — interactive charts, filters, KPI cards, CSV/PDF export
- **Prophet forecasting** — automated ML forecasts on key metrics
- **Slack/email alerting** — notifications when KPIs breach thresholds
- **Dockerised** — one command to run everything
- **GitHub Actions CI/CD** — lint, test, auto-deploy on push

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions CI/CD                  │
└─────────────────────────────────────────────────────────┘
         │ push → test → lint → deploy
         ▼
┌─────────────────────────────────────────────────────────┐
│  DATA SOURCES (CSV / REST API / generated synthetic)    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────┐
│         ETL Pipeline (Python)         │
│  extract → transform → validate       │
│  scheduled via APScheduler            │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│         DuckDB (columnar DB)          │
│  kpis.db — partitioned by date/site   │
└───────┬───────────────────────────────┘
        │
   ┌────┴────┐
   ▼         ▼
┌──────┐  ┌──────────────────────────┐
│ API  │  │   ML Forecasting         │
│ Fast │  │   Prophet / ARIMA        │
│ API  │  │   auto-retrain weekly    │
└──┬───┘  └──────────┬───────────────┘
   │                 │
   └────────┬────────┘
            ▼
┌───────────────────────────────────────┐
│       Streamlit Dashboard             │
│  KPI cards │ Time series │ Forecasts  │
│  Filters   │ Alerts      │ Export     │
└───────────────────────────────────────┘
```

---

## 📁 Project Structure

```
pharma-kpi-platform/
├── pipeline/
│   ├── extract.py          # Data ingestion (CSV, API, synthetic)
│   ├── transform.py        # Cleaning, normalization, KPI computation
│   ├── load.py             # Insert into DuckDB
│   ├── scheduler.py        # APScheduler — runs pipeline every hour
│   └── validate.py         # Great Expectations / pandera schema checks
├── api/
│   ├── main.py             # FastAPI app entry point
│   ├── routers/
│   │   ├── kpis.py         # GET /kpis, GET /kpis/{site}
│   │   ├── forecasts.py    # GET /forecasts/{metric}
│   │   └── alerts.py       # GET /alerts, POST /alerts/rules
│   └── schemas.py          # Pydantic models
├── ml/
│   ├── forecaster.py       # Prophet wrapper for KPI forecasting
│   └── retrain.py          # Weekly auto-retrain logic
├── dashboard/
│   ├── app.py              # Streamlit main app
│   ├── pages/
│   │   ├── overview.py     # Global KPI overview
│   │   ├── site_detail.py  # Per-site drill-down
│   │   └── forecasts.py    # Forecast visualisation page
│   └── components/
│       ├── kpi_card.py     # Reusable KPI card component
│       └── chart.py        # Plotly chart factory
├── alerts/
│   ├── engine.py           # Threshold evaluation logic
│   └── notifier.py         # Slack webhook + email (SMTP)
├── data/
│   ├── raw/                # Raw ingested files
│   ├── processed/          # Transformed data
│   └── kpis.db             # DuckDB database (gitignored)
├── tests/
│   ├── test_pipeline.py
│   ├── test_api.py
│   └── test_forecaster.py
├── .github/
│   └── workflows/
│       └── ci.yml          # CI: lint + test + deploy
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.dashboard
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/BadreddineEK/pharma-kpi-platform
cd pharma-kpi-platform
cp .env.example .env          # fill in your config
docker-compose up --build
```

Then open:
- **Dashboard** → http://localhost:8501
- **API docs** → http://localhost:8000/docs

### Option 2 — Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the ETL pipeline once
python -m pipeline.scheduler --run-once

# Start FastAPI
uvicorn api.main:app --reload --port 8000

# Start Streamlit (separate terminal)
streamlit run dashboard/app.py
```

---

## 📊 KPIs Tracked

| KPI | Description | Alert Threshold |
|-----|-------------|----------------|
| `batch_yield` | Production yield per batch (%) | < 92% |
| `cycle_time` | Manufacturing cycle time (hours) | > 48h |
| `oos_rate` | Out-of-spec rate (%) | > 2% |
| `trials_enrolled` | Clinical trial enrollment count | < target |
| `adverse_events` | Adverse event count per 1000 patients | > 5 |
| `revenue_index` | Normalised revenue index | custom |

---

## 🤖 ML Forecasting

Prophet is used to forecast each KPI 30 days ahead, auto-retrained weekly:

```python
from ml.forecaster import KPIForecaster

forecaster = KPIForecaster(metric="batch_yield", horizon_days=30)
forecast_df = forecaster.run()
```

Forecasts are stored in DuckDB and served via `/forecasts/{metric}`.

---

## 🔔 Alerting

Configure thresholds in `.env` or via the API:

```bash
curl -X POST http://localhost:8000/alerts/rules \
  -H 'Content-Type: application/json' \
  -d '{"metric": "oos_rate", "operator": "gt", "threshold": 2.0, "channel": "slack"}'
```

Set `SLACK_WEBHOOK_URL` in `.env` to receive notifications.

---

## 🧪 Tests

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## ☁️ Deployment

See [DEPLOY.md](./DEPLOY.md) for step-by-step instructions to deploy on:
- **Railway** (recommended, free tier)
- **Render**
- **Self-hosted VPS (Ubuntu)**

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11 |
| Storage | DuckDB 0.10 |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly |
| ML | Prophet + pandas |
| Scheduling | APScheduler |
| Containerisation | Docker + docker-compose |
| CI/CD | GitHub Actions |
| Alerting | Slack Webhooks + SMTP |

---

## 👤 Author

**Badreddine EL KHAMLICHI** — Data Scientist @ Efor (mission Boehringer Ingelheim)

[GitHub](https://github.com/BadreddineEK) · [Portfolio](https://badreddineel.github.io/portfolioBadreddine)
