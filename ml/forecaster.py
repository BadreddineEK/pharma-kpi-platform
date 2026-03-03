"""Prophet-based KPI forecaster."""

import logging
from typing import Optional

import pandas as pd

from pipeline.load import get_connection

logger = logging.getLogger(__name__)


class KPIForecaster:
    def __init__(self, metric: str, horizon_days: int = 30, site: Optional[str] = None):
        self.metric = metric
        self.horizon_days = horizon_days
        self.site = site

    def _load_training_data(self) -> pd.DataFrame:
        con = get_connection()
        query = f"""
            SELECT date AS ds, AVG({self.metric}) AS y
            FROM kpis
            {'WHERE site = ?' if self.site else ''}
            GROUP BY date
            ORDER BY date
        """
        params = [self.site] if self.site else []
        df = con.execute(query, params).df()
        con.close()
        df["ds"] = pd.to_datetime(df["ds"])
        return df

    def run(self) -> pd.DataFrame:
        """Train Prophet model and store forecast in DuckDB."""
        try:
            from prophet import Prophet
        except ImportError:
            logger.error("Prophet not installed. Run: pip install prophet")
            return pd.DataFrame()

        df = self._load_training_data()
        if len(df) < 30:
            logger.warning(f"Not enough data to forecast {self.metric} (need ≥30 points)")
            return pd.DataFrame()

        model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
        model.fit(df)

        future = model.make_future_dataframe(periods=self.horizon_days)
        forecast = model.predict(future)
        forecast = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(self.horizon_days)
        forecast["metric"] = self.metric
        forecast["site"] = self.site

        # Store in DuckDB
        con = get_connection()
        con.execute("DELETE FROM forecasts WHERE metric = ? AND site IS NOT DISTINCT FROM ?", [self.metric, self.site])
        con.execute("INSERT INTO forecasts SELECT ds, yhat, yhat_lower, yhat_upper, metric, site, current_timestamp FROM forecast")
        con.close()

        logger.info(f"Forecast stored for {self.metric} ({self.horizon_days} days)")
        return forecast
