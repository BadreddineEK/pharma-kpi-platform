"""Forecasts page — Prophet predictions per metric."""

import plotly.graph_objects as go
import streamlit as st

from pipeline.load import get_connection

METRICS = ["batch_yield", "cycle_time", "oos_rate", "revenue_index", "adverse_events"]


def render() -> None:
    st.title("🤖 ML Forecasts")
    st.caption("Prophet forecasts — retrained weekly")

    metric = st.selectbox("Select metric", METRICS)

    con = get_connection()
    hist_df = con.execute(f"""
        SELECT date AS ds, AVG({metric}) AS y
        FROM kpis
        WHERE date >= current_date - INTERVAL '90 days'
        GROUP BY date ORDER BY date
    """).df()

    forecast_df = con.execute("""
        SELECT ds, yhat, yhat_lower, yhat_upper FROM forecasts
        WHERE metric = ?
        ORDER BY ds
    """, [metric]).df()
    con.close()

    if forecast_df.empty:
        st.info(f"No forecast available for `{metric}`. Trigger retraining via the API: `POST /forecasts/retrain/{metric}`")
        if st.button("🔄 Trigger retraining now"):
            import httpx, os
            api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            r = httpx.post(f"{api_url}/forecasts/retrain/{metric}")
            st.success(f"Retraining started: {r.json()}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_df["ds"], y=hist_df["y"], name="Historical", line=dict(color="steelblue")))
    fig.add_trace(go.Scatter(x=forecast_df["ds"], y=forecast_df["yhat"], name="Forecast", line=dict(color="orange", dash="dash")))
    fig.add_trace(go.Scatter(
        x=list(forecast_df["ds"]) + list(forecast_df["ds"][::-1]),
        y=list(forecast_df["yhat_upper"]) + list(forecast_df["yhat_lower"][::-1]),
        fill="toself", fillcolor="rgba(255,165,0,0.15)", line=dict(color="rgba(255,255,255,0)"),
        name="Confidence interval"
    ))
    fig.update_layout(title=f"{metric.replace('_', ' ').title()} — 30-day forecast", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
