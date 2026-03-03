"""Load transformed data into DuckDB."""

import logging
import os
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/kpis.db")


def get_connection() -> duckdb.DuckDBPyConnection:
    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(DUCKDB_PATH)


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create tables if they don't exist."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS kpis (
            date DATE,
            site VARCHAR,
            batch_yield DOUBLE,
            cycle_time DOUBLE,
            oos_rate DOUBLE,
            trials_enrolled INTEGER,
            adverse_events DOUBLE,
            revenue_index DOUBLE,
            week INTEGER,
            month INTEGER,
            year INTEGER,
            batch_yield_breach BOOLEAN,
            cycle_time_breach BOOLEAN,
            oos_rate_breach BOOLEAN,
            adverse_events_breach BOOLEAN,
            loaded_at TIMESTAMP DEFAULT current_timestamp
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            metric VARCHAR,
            ds DATE,
            yhat DOUBLE,
            yhat_lower DOUBLE,
            yhat_upper DOUBLE,
            site VARCHAR,
            created_at TIMESTAMP DEFAULT current_timestamp
        )
    """)
    logger.info("Schema initialised")


def upsert_kpis(df: pd.DataFrame, con: duckdb.DuckDBPyConnection) -> int:
    """Insert new records, skip duplicates on (date, site)."""
    existing = con.execute("SELECT date, site FROM kpis").df()
    if not existing.empty:
        existing["date"] = pd.to_datetime(existing["date"]).dt.date
        df["date_key"] = df["date"].dt.date.astype(str)
        existing["date_key"] = existing["date"].astype(str)
        existing_keys = set(zip(existing["date_key"], existing["site"]))
        mask = ~df.apply(lambda r: (r["date_key"], r["site"]) in existing_keys, axis=1)
        df = df[mask].drop(columns=["date_key"])

    if df.empty:
        logger.info("No new records to insert")
        return 0

    con.execute("INSERT INTO kpis SELECT * EXCLUDE (date_key) FROM df") if "date_key" not in df.columns else con.execute("INSERT INTO kpis SELECT * FROM df")
    logger.info(f"Inserted {len(df)} new KPI records")
    return len(df)


def load(df: pd.DataFrame) -> int:
    con = get_connection()
    init_schema(con)
    inserted = upsert_kpis(df, con)
    con.close()
    return inserted
