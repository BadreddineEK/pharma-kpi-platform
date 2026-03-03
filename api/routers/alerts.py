"""Alert management endpoints."""

from typing import List

from fastapi import APIRouter

from api.schemas import AlertEvent, AlertRule
from alerts.engine import evaluate_alerts
from pipeline.load import get_connection
from pipeline.transform import THRESHOLDS

router = APIRouter()


@router.get("/rules")
def get_alert_rules():
    """Return current alert threshold rules."""
    return [
        {"metric": k, "operator": v["operator"], "threshold": v["value"]}
        for k, v in THRESHOLDS.items()
    ]


@router.get("/events", response_model=List[AlertEvent])
def get_alert_events(days: int = 7):
    """Return recent KPI breach events."""
    con = get_connection()
    df = con.execute(f"""
        SELECT date, site, 'batch_yield' as metric, batch_yield as value,
               92.0 as threshold, 'lt' as operator
        FROM kpis
        WHERE batch_yield_breach = true
          AND date >= current_date - INTERVAL '{days} days'
        UNION ALL
        SELECT date, site, 'oos_rate', oos_rate, 2.0, 'gt'
        FROM kpis
        WHERE oos_rate_breach = true
          AND date >= current_date - INTERVAL '{days} days'
        ORDER BY date DESC
        LIMIT 200
    """).df()
    con.close()
    return df.to_dict(orient="records")


@router.post("/evaluate")
def trigger_alert_evaluation():
    """Manually trigger alert evaluation on latest data."""
    fired = evaluate_alerts()
    return {"alerts_fired": fired}
