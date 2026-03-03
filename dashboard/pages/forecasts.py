"""Forecasts page — Prophet predictions per metric (with graceful fallback)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.load import get_connection

METRICS = ["batch_yield", "cycle_time", "oos_rate", "revenue_index", "adverse_events"]


def simple_forecast(series: pd.DataFrame, horizon_days: int = 30) -> pd.DataFrame:
    """Lightweight linear-trend + weekly seasonality forecast (no Prophet needed)."""
    from sklearn.linear_model import LinearRegression

    df = series.copy()
    df["t"] = (pd.to_datetime(df["ds"]) - pd.to_datetime(df["ds"]).min()).dt.days
    df["dow"] = pd.to_datetime(df["ds"]).dt.dayofweek

    # One-hot encode day of week
    dow_dummies = pd.get_dummies(df["dow"], prefix="dow")
    X = pd.concat([df[["t"]], dow_dummies], axis=1)
    y = df["y"].values

    model = LinearRegression().fit(X, y)

    last_t = df["t"].max()
    last_date = pd.to_datetime(df["ds"]).max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days)
    future_t = np.arange(last_t + 1, last_t + 1 + horizon_days)
    future_dow = future_dates.dayofweek

    future_dow_dummies = pd.DataFrame(
        {f"dow_{i}": (future_dow == i).astype(int) for i in range(7)}
    )
    X_future = pd.concat([pd.DataFrame({"t": future_t}), future_dow_dummies], axis=1)
    # Align columns
    for col in X.columns:
        if col not in X_future.columns:
            X_future[col] = 0
    X_future = X_future[X.columns]

    yhat = model.predict(X_future)
    residuals = y - model.predict(X)
    std = np.std(residuals)

    return pd.DataFrame({
        "ds": future_dates,
        "yhat": yhat,
        "yhat_lower": yhat - 1.96 * std,
        "yhat_upper": yhat + 1.96 * std,
    })


def render() -> None:
    st.title("🤖 ML Forecasts")
    st.caption("Linear trend + weekly seasonality forecast — 30 days ahead")
    st.info("💡 Prophet is disabled on the live demo to keep deps light. Forecasts use a linear regression model with weekly seasonality. Swap in Prophet locally for full accuracy.", icon="ℹ️")

    metric = st.selectbox("Select metric", METRICS)
    horizon = st.slider("Forecast horizon (days)", 7, 60, 30)

    con = get_connection()
    hist_df = con.execute(f"""
        SELECT date AS ds, AVG({metric}) AS y
        FROM kpis
        WHERE date >= current_date - INTERVAL '180 days'
        GROUP BY date ORDER BY date
    """).df()
    con.close()

    if hist_df.empty or len(hist_df) < 14:
        st.warning("Not enough historical data to forecast.")
        return

    forecast_df = simple_forecast(hist_df, horizon_days=horizon)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_df["ds"], y=hist_df["y"],
        name="Historical", line=dict(color="#4C9BE8", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df["ds"], y=forecast_df["yhat"],
        name="Forecast", line=dict(color="#F4A261", width=2, dash="dash")
    ))
    fig.add_trace(go.Scatter(
        x=list(forecast_df["ds"]) + list(forecast_df["ds"][::-1]),
        y=list(forecast_df["yhat_upper"]) + list(forecast_df["yhat_lower"][::-1]),
        fill="toself",
        fillcolor="rgba(244,162,97,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="95% confidence"
    ))
    fig.update_layout(
        title=f"{metric.replace('_', ' ').title()} — {horizon}-day forecast",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Forecast data"):
        st.dataframe(forecast_df.round(2), use_container_width=True)
        csv = forecast_df.to_csv(index=False).encode()
        st.download_button("⬇️ Download forecast CSV", csv, f"{metric}_forecast.csv", "text/csv")
