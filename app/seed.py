"""Generate synthetic pharma KPI data and populate DuckDB (runs once per session).

Each site has distinct operational characteristics reflecting real-world variance
across manufacturing facilities. Incidents (consecutive quality dips) and a gentle
positive trend on batch yield simulate continuous-improvement programs.
"""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import streamlit as st

_default_db = str(Path(tempfile.gettempdir()) / "kpis.db")
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", _default_db)
SITES = ["Lyon", "Paris", "Strasbourg", "Bordeaux"]

# Per-site baselines — reflects realistic inter-site variance
# (batch_yield_mu, cycle_time_mu, oos_rate_scale, adverse_scale, rev_mu)
SITE_PROFILES = {
    "Lyon":       dict(yield_mu=96.0, yield_sd=1.5, ct_mu=33, ct_sd=4, oos_sc=0.7,  adv_sc=1.5, rev_mu=104),
    "Paris":      dict(yield_mu=94.5, yield_sd=2.0, ct_mu=40, ct_sd=5, oos_sc=1.1,  adv_sc=2.0, rev_mu=100),
    "Strasbourg": dict(yield_mu=95.0, yield_sd=1.8, ct_mu=37, ct_sd=5, oos_sc=1.0,  adv_sc=1.8, rev_mu=101),
    "Bordeaux":   dict(yield_mu=93.5, yield_sd=2.5, ct_mu=42, ct_sd=6, oos_sc=1.6,  adv_sc=2.5, rev_mu=97),
}

N_DAYS = 365


def _inject_incidents(arr: np.ndarray, breach_val: float, n_incidents: int = 4,
                      window: int = 7) -> np.ndarray:
    """Overwrite random windows with breach-level values to simulate quality incidents."""
    rng = np.random.default_rng(seed=int(abs(breach_val) * 100))
    starts = rng.choice(N_DAYS - window, size=n_incidents, replace=False)
    for s in starts:
        arr[s:s + window] = breach_val + rng.normal(0, abs(breach_val) * 0.05, window)
    return arr


def get_con():
    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(DUCKDB_PATH)


@st.cache_resource(show_spinner="⏳ Loading demo data…")
def seed_database():
    con = get_con()
    con.execute("""
        CREATE TABLE IF NOT EXISTS kpis (
            date        DATE,
            site        VARCHAR,
            batch_yield DOUBLE,
            cycle_time  DOUBLE,
            oos_rate    DOUBLE,
            trials_enrolled INTEGER,
            adverse_events  DOUBLE,
            revenue_index   DOUBLE
        )
    """)
    if con.execute("SELECT COUNT(*) FROM kpis").fetchone()[0] > 0:
        con.close()
        return True

    np.random.seed(42)
    base = datetime.now() - timedelta(days=N_DAYS)
    t = np.arange(N_DAYS)  # day index for trend

    all_records = []
    for site, p in SITE_PROFILES.items():
        # Slight positive trend on batch yield (~0.003%/day improvement, CI program)
        trend = 0.003 * t

        batch_yield = np.clip(
            np.random.normal(p["yield_mu"], p["yield_sd"], N_DAYS) + trend,
            82, 100,
        )
        # Inject 3 incident windows where yield drops below threshold
        batch_yield = _inject_incidents(batch_yield, breach_val=89.0)

        cycle_time = np.clip(
            np.random.normal(p["ct_mu"], p["ct_sd"], N_DAYS),
            18, 80,
        )
        # Inject 2 windows of elevated cycle time
        cycle_time = _inject_incidents(cycle_time, breach_val=51.0, n_incidents=2)

        oos_rate = np.clip(
            np.random.exponential(p["oos_sc"], N_DAYS),
            0, 10,
        )
        oos_rate = _inject_incidents(oos_rate, breach_val=2.8, n_incidents=2, window=5)

        adverse_events = np.clip(
            np.random.exponential(p["adv_sc"], N_DAYS),
            0, 20,
        )

        revenue_index = np.clip(
            np.random.normal(p["rev_mu"], 8, N_DAYS)
            + 0.005 * t  # slight positive revenue trend
            + 3 * np.sin(2 * np.pi * t / 90),   # quarterly seasonality
            60, 140,
        )

        trials_enrolled = np.random.poisson(45, N_DAYS)

        for day in range(N_DAYS):
            all_records.append({
                "date":            (base + timedelta(days=day)).date(),
                "site":            site,
                "batch_yield":     float(batch_yield[day]),
                "cycle_time":      float(cycle_time[day]),
                "oos_rate":        float(oos_rate[day]),
                "trials_enrolled": int(trials_enrolled[day]),
                "adverse_events":  float(adverse_events[day]),
                "revenue_index":   float(revenue_index[day]),
            })

    df = pd.DataFrame(all_records)
    con.execute("INSERT INTO kpis SELECT * FROM df")
    con.close()
    return True
