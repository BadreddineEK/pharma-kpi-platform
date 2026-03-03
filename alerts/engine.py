"""Alert evaluation engine — checks latest KPI data against thresholds."""

import logging
import os
from typing import List

import pandas as pd

from alerts.notifier import send_slack_alert
from pipeline.load import get_connection
from pipeline.transform import THRESHOLDS

logger = logging.getLogger(__name__)


def evaluate_alerts(lookback_hours: int = 2) -> List[dict]:
    """Check recent KPI data for threshold breaches and fire alerts."""
    con = get_connection()
    df = con.execute("""
        SELECT * FROM kpis
        WHERE date = (SELECT MAX(date) FROM kpis)
    """).df()
    con.close()

    if df.empty:
        logger.info("No data to evaluate")
        return []

    fired = []
    breach_cols = {
        "batch_yield_breach": "batch_yield",
        "cycle_time_breach": "cycle_time",
        "oos_rate_breach": "oos_rate",
        "adverse_events_breach": "adverse_events",
    }

    for breach_col, metric in breach_cols.items():
        breached = df[df[breach_col] == True]
        for _, row in breached.iterrows():
            alert = {
                "metric": metric,
                "site": row["site"],
                "value": round(row[metric], 2),
                "threshold": THRESHOLDS[metric]["value"],
                "date": str(row["date"]),
            }
            fired.append(alert)
            logger.warning(f"🚨 Alert: {metric} = {alert['value']} at {alert['site']} (threshold: {alert['threshold']})")

            slack_url = os.getenv("SLACK_WEBHOOK_URL")
            if slack_url:
                send_slack_alert(alert, slack_url)

    return fired
