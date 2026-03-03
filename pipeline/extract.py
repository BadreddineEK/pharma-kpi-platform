"""Data extraction: generates synthetic pharma KPI data.

In production, replace generate_synthetic_data() with real API calls
or CSV ingestion from your data sources.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SITES = ["Lyon", "Paris", "Strasbourg", "Bordeaux"]
METRICS = ["batch_yield", "cycle_time", "oos_rate", "trials_enrolled", "adverse_events", "revenue_index"]


def generate_synthetic_data(days: int = 365, output_dir: str = "data/raw") -> pd.DataFrame:
    """Generate realistic synthetic pharma KPI data."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    records = []
    base_date = datetime.now() - timedelta(days=days)

    np.random.seed(42)
    for day in range(days):
        current_date = base_date + timedelta(days=day)
        for site in SITES:
            records.append({
                "date": current_date.date(),
                "site": site,
                "batch_yield": np.clip(np.random.normal(95, 2), 85, 100),
                "cycle_time": np.clip(np.random.normal(36, 5), 20, 72),
                "oos_rate": np.clip(np.random.exponential(1.2), 0, 8),
                "trials_enrolled": int(np.random.poisson(45)),
                "adverse_events": np.clip(np.random.exponential(2), 0, 15),
                "revenue_index": np.clip(np.random.normal(100, 10), 60, 140),
            })

    df = pd.DataFrame(records)
    output_path = Path(output_dir) / f"kpis_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Extracted {len(df)} records → {output_path}")
    return df


def load_latest_raw(raw_dir: str = "data/raw") -> pd.DataFrame:
    """Load the most recently extracted raw file."""
    raw_path = Path(raw_dir)
    files = sorted(raw_path.glob("*.parquet"))
    if not files:
        logger.warning("No raw files found, generating synthetic data...")
        return generate_synthetic_data()
    latest = files[-1]
    logger.info(f"Loading raw file: {latest}")
    return pd.read_parquet(latest)
