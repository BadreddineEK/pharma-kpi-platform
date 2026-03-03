"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import alerts, forecasts, kpis

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Pharma KPI Platform API",
    description="REST API for pharma KPI data, forecasts and alerting",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kpis.router, prefix="/kpis", tags=["KPIs"])
app.include_router(forecasts.router, prefix="/forecasts", tags=["Forecasts"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}
