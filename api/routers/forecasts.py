"""Forecast endpoints."""

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.schemas import ForecastPoint
from pipeline.load import get_connection

router = APIRouter()


@router.get("/{metric}", response_model=List[ForecastPoint])
def get_forecast(
    metric: str,
    site: Optional[str] = Query(None),
    horizon_days: int = Query(30),
):
    """Return stored forecast for a given metric."""
    con = get_connection()
    query = """
        SELECT ds, yhat, yhat_lower, yhat_upper, metric, site
        FROM forecasts
        WHERE metric = ?
        AND ds >= current_date
        AND ds <= current_date + INTERVAL '? days'
        ORDER BY ds
    """
    df = con.execute("SELECT * FROM forecasts WHERE metric = ? ORDER BY ds", [metric]).df()
    con.close()
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast found for metric '{metric}'. Trigger retraining first.",
        )
    return df.to_dict(orient="records")


@router.post("/retrain/{metric}")
def retrain_forecast(metric: str, background_tasks: BackgroundTasks, site: Optional[str] = Query(None)):
    """Trigger forecast retraining for a metric (runs in background)."""
    from ml.forecaster import KPIForecaster
    background_tasks.add_task(KPIForecaster(metric=metric, site=site).run)
    return {"message": f"Retraining started for metric '{metric}'", "site": site}
