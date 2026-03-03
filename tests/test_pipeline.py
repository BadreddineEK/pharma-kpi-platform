"""Unit tests for the ETL pipeline."""

import pandas as pd
import pytest

from pipeline.extract import generate_synthetic_data
from pipeline.transform import transform


def test_extract_returns_dataframe():
    df = generate_synthetic_data(days=10, output_dir="/tmp/test_raw")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10 * 4  # 10 days × 4 sites
    assert "batch_yield" in df.columns


def test_extract_columns():
    df = generate_synthetic_data(days=5, output_dir="/tmp/test_raw")
    expected = {"date", "site", "batch_yield", "cycle_time", "oos_rate",
                "trials_enrolled", "adverse_events", "revenue_index"}
    assert expected.issubset(set(df.columns))


def test_transform_adds_breach_flags():
    df = generate_synthetic_data(days=30, output_dir="/tmp/test_raw")
    transformed = transform(df)
    assert "batch_yield_breach" in transformed.columns
    assert "oos_rate_breach" in transformed.columns
    assert transformed["batch_yield_breach"].dtype == bool


def test_transform_no_duplicates():
    df = generate_synthetic_data(days=10, output_dir="/tmp/test_raw")
    # Duplicate rows
    df_dup = pd.concat([df, df])
    transformed = transform(df_dup)
    assert transformed.duplicated(subset=["date", "site"]).sum() == 0


def test_batch_yield_in_valid_range():
    df = generate_synthetic_data(days=30, output_dir="/tmp/test_raw")
    assert df["batch_yield"].between(0, 100).all()


def test_oos_rate_non_negative():
    df = generate_synthetic_data(days=30, output_dir="/tmp/test_raw")
    assert (df["oos_rate"] >= 0).all()
