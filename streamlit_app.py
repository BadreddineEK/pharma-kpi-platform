"""Streamlit Cloud entry point.

This file is at the repo root so Streamlit Cloud auto-detects it.
It seeds the DuckDB database on first run, then loads the dashboard.
"""

import os
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

# Use /tmp for DuckDB on Streamlit Cloud (ephemeral, writable)
os.environ.setdefault("DUCKDB_PATH", "/tmp/kpis.db")
os.environ.setdefault("DATA_RAW_PATH", "/tmp/data/raw")
os.environ.setdefault("DATA_PROCESSED_PATH", "/tmp/data/processed")
os.environ.setdefault("API_BASE_URL", "http://localhost:8000")

import streamlit as st

# ── Seed DB once per session ────────────────────────────────────────────────
@st.cache_resource(show_spinner="⏳ Seeding demo data (first load only)...")
def seed_database():
    """Run the ETL pipeline once to populate DuckDB with synthetic demo data."""
    from pipeline.extract import generate_synthetic_data
    from pipeline.load import get_connection, init_schema
    from pipeline.transform import transform

    raw_df = generate_synthetic_data(days=365, output_dir="/tmp/data/raw")
    transformed_df = transform(raw_df)

    con = get_connection()
    init_schema(con)

    # Only insert if table is empty
    count = con.execute("SELECT COUNT(*) FROM kpis").fetchone()[0]
    if count == 0:
        con.execute("INSERT INTO kpis SELECT * FROM transformed_df")
    con.close()
    return True


seed_database()

# ── Load the main dashboard ─────────────────────────────────────────────────
from dashboard.app import *
