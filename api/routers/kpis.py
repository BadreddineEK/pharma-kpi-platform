"""KPI data endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas import KPIRecord
from pipeline.load import get_connection

router = APIRouter()


@router.get("/", response_model=List[KPIRecord])
def get_kpis(
    site: Optional[str] = Query(None, description="Filter by site"),
    metric: Optional[str] = Query(None, description="Filter by metric name"),
    days: int = Query(30, description="Number of days to return"),
):
    """Return KPI records for the last N days, optionally filtered by site."""
    con = get_connection()
    query = f"""
        SELECT *
        FROM kpis
        WHERE date >= current_date - INTERVAL '{days} days'
        {'AND site = ?' if site else ''}
        ORDER BY date DESC, site
        LIMIT 10000
    """
    params = [site] if site else []
    df = con.execute(query, params).df()
    con.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="No KPI data found. Run the pipeline first.")
    return df.to_dict(orient="records")


@router.get("/summary")
def get_kpi_summary(days: int = Query(30)):
    """Return aggregated KPI summary (mean, min, max, breach count) per site."""
    con = get_connection()
    df = con.execute(f"""
        SELECT
            site,
            ROUND(AVG(batch_yield), 2) AS avg_batch_yield,
            ROUND(AVG(cycle_time), 2) AS avg_cycle_time,
            ROUND(AVG(oos_rate), 2) AS avg_oos_rate,
            ROUND(AVG(revenue_index), 2) AS avg_revenue_index,
            SUM(CAST(batch_yield_breach AS INTEGER)) AS batch_yield_breaches,
            SUM(CAST(oos_rate_breach AS INTEGER)) AS oos_rate_breaches
        FROM kpis
        WHERE date >= current_date - INTERVAL '{days} days'
        GROUP BY site
        ORDER BY site
    """).df()
    con.close()
    return df.to_dict(orient="records")


@router.get("/sites")
def get_sites():
    """Return list of available sites."""
    con = get_connection()
    sites = con.execute("SELECT DISTINCT site FROM kpis ORDER BY site").df()["site"].tolist()
    con.close()
    return {"sites": sites}
