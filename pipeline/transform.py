"""Data transformation: cleaning, normalization and KPI enrichment."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Alert thresholds — also used by the alerting engine
THRESHOLDS = {
    "batch_yield": {"operator": "lt", "value": 92.0},
    "cycle_time": {"operator": "gt", "value": 48.0},
    "oos_rate": {"operator": "gt", "value": 2.0},
    "adverse_events": {"operator": "gt", "value": 5.0},
}


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Clean, enrich and validate raw KPI data."""
    df = df.copy()

    # Ensure date type
    df["date"] = pd.to_datetime(df["date"])

    # Round floats
    float_cols = ["batch_yield", "cycle_time", "oos_rate", "adverse_events", "revenue_index"]
    df[float_cols] = df[float_cols].round(2)

    # Add derived columns
    df["week"] = df["date"].dt.isocalendar().week.astype(int)
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    # Flag breaches
    df["batch_yield_breach"] = df["batch_yield"] < THRESHOLDS["batch_yield"]["value"]
    df["cycle_time_breach"] = df["cycle_time"] > THRESHOLDS["cycle_time"]["value"]
    df["oos_rate_breach"] = df["oos_rate"] > THRESHOLDS["oos_rate"]["value"]
    df["adverse_events_breach"] = df["adverse_events"] > THRESHOLDS["adverse_events"]["value"]

    # Drop duplicates
    df = df.drop_duplicates(subset=["date", "site"])
    df = df.sort_values(["date", "site"]).reset_index(drop=True)

    logger.info(f"Transformed {len(df)} records")
    return df
