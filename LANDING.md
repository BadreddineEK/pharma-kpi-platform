# 💊 Pharma KPI Platform

> **Real-time manufacturing intelligence for regulated pharmaceutical networks.**  
> Monitor GMP compliance, forecast KPI drift, and triage alerts — across all your sites, in one place.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-red?logo=streamlit)](https://pharma-kpi-platform.streamlit.app)
[![GitHub](https://img.shields.io/badge/GitHub-Open%20Source-black?logo=github)](https://github.com/BadreddineEK/pharma-kpi-platform)

---

## 🎯 The Problem

Pharmaceutical manufacturers operate under EMA/FDA GMP regulations where a **single batch breach** can trigger:
- 🚨 A regulatory hold — production stops immediately
- 💸 Millions in penalties and recall costs  
- 📉 Reputational damage and delayed product launches

Most Quality teams still rely on **Excel sheets and email chains** to track KPI compliance across sites. By the time a drift is detected, it's already a crisis.

---

## ✅ The Solution

Pharma KPI Platform gives your Data & Quality teams a **single live view** across all manufacturing sites:

| Feature | What it does |
|---|---|
| 🏠 **Network Overview** | Compliance heatmap, rolling trends, OOS & cycle time distributions across all sites |
| 🔬 **Site Drill-down** | Per-site KPI trends, weekly breach calendar, radar compliance profile |
| 📈 **ML Forecasting** | 7–90 day KPI projections with 95% prediction intervals — catch drift before it happens |
| 🚨 **Alert Management** | Critical/Warning breach triage with filterable tables and timeline charts |
| 📊 **KPI Comparison** | Side-by-side site benchmarking across all regulated metrics |

---

## 🛠️ Architecture

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
              Plotly interactive charts
                            ↓
                   End user (browser)
```

**Stack:** Python 3.11+ · Streamlit · DuckDB · FastAPI · Plotly · scikit-learn · Docker · GitHub Actions CI

---

## 💰 Pricing

> *Indicative SaaS pricing — for enterprise licensing enquiries, contact below.*

| Plan | Price | Sites | Users | Features |
|---|---|---|---|---|
| **Starter** | €490/mo | 1 site | 3 users | Overview + Alerts, 90-day history |
| **Pro** | €1 490/mo | Up to 5 sites | 15 users | All pages + Forecasting + CSV exports, 2-year history |
| **Enterprise** | Custom | Unlimited | Unlimited | Custom KPIs, API access, SSO, on-premise deployment, SLA |

> 💡 All plans include a **30-day free trial** and onboarding support.

---

## 🏭 Built For

- **Quality Assurance teams** tracking GMP compliance across multi-site networks
- **Data Engineering teams** in regulated industries (pharma, medtech, biotech)
- **Operations managers** needing live supply chain & production KPI visibility
- **Regulatory affairs** teams preparing for EMA/FDA inspections

**Reference companies:** Sanofi · Boehringer Ingelheim · Pfizer · Roche · Servier · Pierre Fabre

---

## 🚀 Try It Now

```bash
git clone https://github.com/BadreddineEK/pharma-kpi-platform
cd pharma-kpi-platform
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Or hit the **[Live Demo →](https://pharma-kpi-platform.streamlit.app)** directly.

---

## 👤 Contact

**Badreddine EL KHAMLICHI** — Data Scientist  
📍 Lyon, France | Efor × Boehringer Ingelheim  
🔗 [GitHub](https://github.com/BadreddineEK) · [LinkedIn](https://linkedin.com/in/badreddineek)  
📧 Open to freelance missions and B2B partnerships
