"""Pydantic models for API request/response validation."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class KPIRecord(BaseModel):
    date: date
    site: str
    batch_yield: float
    cycle_time: float
    oos_rate: float
    trials_enrolled: int
    adverse_events: float
    revenue_index: float
    batch_yield_breach: bool
    cycle_time_breach: bool
    oos_rate_breach: bool
    adverse_events_breach: bool


class ForecastPoint(BaseModel):
    ds: date
    yhat: float
    yhat_lower: float
    yhat_upper: float
    metric: str
    site: Optional[str] = None


class AlertRule(BaseModel):
    metric: str
    operator: str  # 'gt' | 'lt'
    threshold: float
    channel: str  # 'slack' | 'email'


class AlertEvent(BaseModel):
    date: date
    site: str
    metric: str
    value: float
    threshold: float
    operator: str
