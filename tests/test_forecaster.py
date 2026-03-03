"""Tests for the ML forecaster."""

import pandas as pd
import pytest

from ml.forecaster import KPIForecaster


def test_forecaster_instantiation():
    f = KPIForecaster(metric="batch_yield", horizon_days=14)
    assert f.metric == "batch_yield"
    assert f.horizon_days == 14


def test_forecaster_no_data_returns_empty(tmp_path, monkeypatch):
    """Returns empty DataFrame when there's not enough data."""
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "empty.db"))
    import importlib
    import pipeline.load as load_mod
    importlib.reload(load_mod)

    f = KPIForecaster(metric="batch_yield", horizon_days=7)
    result = f.run()
    assert isinstance(result, pd.DataFrame)
