"""Basic tests for seed and data generation."""
import os
import tempfile

import pandas as pd

os.environ["DUCKDB_PATH"] = tempfile.mktemp(suffix=".db")


def test_seed_creates_data():
    from app.seed import get_con, seed_database
    seed_database()
    con = get_con()
    count = con.execute("SELECT COUNT(*) FROM kpis").fetchone()[0]
    con.close()
    assert count == 365 * 4


def test_data_columns():
    from app.seed import get_con
    con = get_con()
    df = con.execute("SELECT * FROM kpis LIMIT 5").df()
    con.close()
    expected = {"date", "site", "batch_yield", "cycle_time", "oos_rate",
                "trials_enrolled", "adverse_events", "revenue_index"}
    assert expected.issubset(set(df.columns))


def test_batch_yield_range():
    from app.seed import get_con
    con = get_con()
    df = con.execute("SELECT batch_yield FROM kpis").df()
    con.close()
    assert df["batch_yield"].between(0, 100).all()
