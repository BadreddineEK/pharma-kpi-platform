"""Generate synthetic data and populate DuckDB (runs once per session)."""
import os
from datetime import datetime, timedelta

import duckdb
import numpy as np
import pandas as pd
import streamlit as st

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "/tmp/kpis.db")
SITES = ["Lyon", "Paris", "Strasbourg", "Bordeaux"]


def get_con():
    return duckdb.connect(DUCKDB_PATH)


@st.cache_resource(show_spinner="⏳ Loading demo data...")
def seed_database():
    con = get_con()
    con.execute("""
        CREATE TABLE IF NOT EXISTS kpis (
            date DATE,
            site VARCHAR,
            batch_yield DOUBLE,
            cycle_time DOUBLE,
            oos_rate DOUBLE,
            trials_enrolled INTEGER,
            adverse_events DOUBLE,
            revenue_index DOUBLE
        )
    """)
    count = con.execute("SELECT COUNT(*) FROM kpis").fetchone()[0]
    if count == 0:
        np.random.seed(42)
        records = []
        base = datetime.now() - timedelta(days=365)
        for day in range(365):
            d = (base + timedelta(days=day)).date()
            for site in SITES:
                records.append({
                    "date": d,
                    "site": site,
                    "batch_yield": float(np.clip(np.random.normal(95, 2), 85, 100)),
                    "cycle_time": float(np.clip(np.random.normal(36, 5), 20, 72)),
                    "oos_rate": float(np.clip(np.random.exponential(1.2), 0, 8)),
                    "trials_enrolled": int(np.random.poisson(45)),
                    "adverse_events": float(np.clip(np.random.exponential(2), 0, 15)),
                    "revenue_index": float(np.clip(np.random.normal(100, 10), 60, 140)),
                })
        df = pd.DataFrame(records)
        con.execute("INSERT INTO kpis SELECT * FROM df")
    con.close()
    return True
