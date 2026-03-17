# 💊 Pharma KPI Platform

> Real-time manufacturing KPI monitoring dashboard for a multi-site pharmaceutical
> network — built as a portfolio project to demonstrate end-to-end data science and
> engineering skills in a regulated-industry context.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red?logo=streamlit)](https://streamlit.io)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.4+-yellow)](https://duckdb.org)
[![Plotly](https://img.shields.io/badge/Plotly-5.20+-purple)](https://plotly.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.5+-orange?logo=scikit-learn)](https://scikit-learn.org)
[![CI](https://github.com/BadreddineEK/pharma-kpi-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/BadreddineEK/pharma-kpi-platform/actions)

---

## 🎯 Problem Statement

Pharmaceutical manufacturers operate under strict GMP (Good Manufacturing Practice)
regulations enforced by the EMA and FDA. A single batch falling below specification,
or a cycle time drifting above the acceptable limit, can trigger a regulatory hold,
a product recall, and millions in penalties.

Quality and Data teams need a **single view** across all sites to:
- Detect compliance drifts *before* they become regulatory events
- Benchmark sites against one another and against corporate targets
- Forecast future KPI behaviour to anticipate problems
- Track and triage breach events in a structured, auditable way

This platform is that tool.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHARMA KPI PLATFORM                          │
│                                                                 │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌─────────┐  │
│  │  ETL     │───▶│  DuckDB   │───▶│ FastAPI  │───▶│Streamlit│  │
│  │ Pipeline │    │ Columnar  │    │  REST    │    │Dashboard│  │
│  │(seed.py) │    │    DB     │    │   API    │    │  (UI)   │  │
│  └──────────┘    └─────┬─────┘    └──────────┘    └────┬────┘  │
│                        │                               │        │
│                  ┌─────▼─────┐                  ┌─────▼─────┐  │
│                  │  ML Layer │                  │  Alerting │  │
│                  │(scikit-   │                  │  Engine   │  │
│                  │ learn OLS)│                  │(Critical/ │  │
│                  └───────────┘                  │ Warning)  │  │
│                                                 └───────────┘  │
└─────────────────────────────────────────────────────────────────┘

Data Flow:
Synthetic Generator → DuckDB (columnar store)
                            ↓
               SQL queries (pandas via duckdb)
                            ↓
        Streamlit dashboard  ←→  scikit-learn forecasting
                            ↓
              Plotly interactive charts  →  End user (browser)
```

---

## 🛠️ Stack

| Layer | Technology | Why |
|---|---|---|
| **Dashboard** | Streamlit 1.32+ | Rapid interactive UI — standard for internal data apps |
| **Storage** | DuckDB 1.4+ | Columnar, zero-config, fast analytical queries on time-series data |
| **Visualisation** | Plotly 5.20+ | Publication-quality interactive charts |
| **ML / Forecasting** | scikit-learn 1.5+ | Lightweight OLS with seasonality — interpretable and fast |
| **Data wrangling** | pandas 2.2+ / numpy 2.0+ | Industry standard |
| **CI/CD** | GitHub Actions | Lint (ruff) + pytest on every push |
| **Linting** | ruff | 10–50× faster than flake8/pylint |

---

## 📊 Dashboard Pages

### 🏠 Overview
Network-wide snapshot across all 4 manufacturing sites.
- **KPI metric cards** with live compliance badges (✅ Compliant / ⚠️ At Risk / 🔴 Breaching)
- **Site Compliance Matrix** — heatmap of compliance % per site × KPI
- **7-day rolling avg Batch Yield** time series, per site, with regulatory floor line
- **OOS Rate & Cycle Time** box plots — outlier detection at a glance
- **Revenue Index** area chart with quarterly seasonality visible
- Full CSV export

### 🔬 Site Detail
Drill into any manufacturing site across three sub-tabs:
- **📉 Trend** — daily + 7-day rolling average for any KPI, threshold overlay, metric description
- **📅 Breach Calendar** — stacked bars of weekly breach days per regulated KPI
- **🕸️ Site Profile** — radar chart of normalised compliance scores for quick diagnosis

### 📈 Forecast
ML-based projection for any KPI, by site or network average:
- Feature-engineered OLS: linear trend (`t` index) + 6 one-hot day-of-week dummies (weekly seasonality)
- Adjustable horizon: 7 to 90 days
- **95 % prediction interval** shaded on the chart
- Model stats: R², RMSE, MAE, trend coefficient, residual σ
- Full model explainability in an expandable panel — interview-ready

### 🚨 Alerts
Structured breach management view:
- **Severity classification**: Critical (>10 % deviation beyond threshold) / Warning (≤10 %)
- Filterable breach table (by site and severity)
- Daily breach timeline — stacked bar by KPI
- Breach distribution: donut by KPI, bar by site

### 📊 KPI Comparison *(new)*
Side-by-side multi-site benchmarking:
- **Grouped bar chart** comparing the latest 30-day average of any KPI across all sites
- **Percentile ranking table** — ranks each site on each regulated KPI
- **Site delta heatmap** — deviation of each site from the network average
- Quickly identifies which site is leading and which is lagging on each dimension

---

## 📐 KPI Catalogue

| KPI | Unit | Threshold | Regulatory basis |
|---|---|---|---|
| **Batch Yield** | % | ≥ 92 % | GMP / 21 CFR Part 211 |
| **Cycle Time** | h | ≤ 48 h | Internal operational standard |
| **OOS Rate** | % | ≤ 2 % | ICH Q10 — CAPA trigger |
| **Adverse Events** | count | ≤ 5 | EMA pharmacovigilance guidelines |
| **Revenue Index** | index | — | Financial reporting |
| **Trials Enrolled** | count | — | Clinical operations |

---

## 🧪 Synthetic Data Design

**1 460 daily records** (365 days × 4 sites) stored in DuckDB.

Each site has distinct baselines reflecting realistic inter-site variance:

| Site | Yield baseline | Cycle Time | Operational profile |
|---|---|---|---|
| **Lyon** | 96.0 % | 33 h | Best-in-class — the reference site |
| **Paris** | 94.5 % | 40 h | Solid, slightly elevated OOS |
| **Strasbourg** | 95.0 % | 37 h | Average performer |
| **Bordeaux** | 93.5 % | 42 h | Oldest equipment — most breaches |

Realism features:
- **Site-specific σ** on every KPI
- **Incident windows** — consecutive days of quality dips simulating real events
  (equipment failure, raw material lot issue, operator changeover)
- **Continuous-improvement trend** on batch yield (+0.003 %/day — CI programme)
- **Quarterly revenue seasonality** (sine wave, 90-day period)
- Reproducible: `np.random.seed(42)`

---

## 🚀 Quickstart

```bash
# 1. Clone
git clone https://github.com/BadreddineEK/pharma-kpi-platform
cd pharma-kpi-platform

# 2. Install (Python 3.11+)
pip install -r requirements.txt

# 3. Run
streamlit run streamlit_app.py
# → http://localhost:8501
```

On first launch a spinner appears while 1 460 rows are seeded into DuckDB (~2 s).
Subsequent launches are instant (Streamlit cache_resource).

**Optional — persistent local DB:**
```bash
# Linux / macOS
export DUCKDB_PATH=data/kpis.db

# Windows PowerShell
$env:DUCKDB_PATH = "data/kpis.db"
```

---

## 🔬 Tests & CI

```bash
pytest tests/ -v
```

GitHub Actions runs on every push to `main`:
1. `ruff check app/ tests/` — linting (PEP 8 + style)
2. `pytest tests/` — unit tests (seed correctness, pipeline stubs, API stubs)

---

## 📁 Repository Structure

```
pharma-kpi-platform/
├── streamlit_app.py        ← Entry point (Streamlit Cloud + local run)
├── LANDING.md              ← Product landing page with pricing
├── app/
│   ├── seed.py             ← Synthetic data generator → DuckDB
│   └── dashboard.py        ← Full dashboard (5 pages)
├── tests/
│   ├── test_seed.py        ← pytest — DB seeding correctness
│   ├── test_api.py         ← pytest — API stubs
│   └── test_pipeline.py    ← pytest — pipeline stubs
├── .streamlit/
│   └── config.toml         ← Dark theme + server config
├── requirements.txt        ← 7 runtime dependencies
└── ruff.toml               ← Linting configuration
```

---

## 🗺️ Roadmap (v2)

- [ ] **FastAPI backend** — REST endpoints serving KPIs from DuckDB
- [ ] **Docker Compose** — one-command full-stack deployment
- [ ] **Prophet forecasting** — seasonal decomposition with holiday effects
- [ ] **Slack / email alerting** — webhook notifications on Critical breaches
- [ ] **APScheduler** — automated daily data refresh pipeline

---

## 👤 Author

**Badreddine EL KHAMLICHI** — Data Scientist  
📍 Lyon, France | Efor × Boehringer Ingelheim  
[GitHub](https://github.com/BadreddineEK) ·
[LinkedIn](https://linkedin.com/in/badreddineek)

> *Built to demonstrate production-grade data engineering, KPI modelling, and ML
> skills in a regulated-industry context — the kind of work done daily at companies
> like Boehringer Ingelheim, Sanofi, or Pfizer.*
