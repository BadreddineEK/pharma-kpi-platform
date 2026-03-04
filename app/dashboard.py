"""Main Streamlit dashboard."""
import os

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import streamlit as st

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "/tmp/kpis.db")
THRESHOLDS = {
    "batch_yield": ("lt", 92.0),
    "cycle_time": ("gt", 48.0),
    "oos_rate": ("gt", 2.0),
    "adverse_events": ("gt", 5.0),
}


def get_con():
    return duckdb.connect(DUCKDB_PATH)


def load_data(days: int, site: str = None) -> pd.DataFrame:
    con = get_con()
    q = f"""
        SELECT * FROM kpis
        WHERE date >= current_date - INTERVAL '{days} days'
        {'AND site = ?' if site else ''}
        ORDER BY date, site
    """
    df = con.execute(q, [site] if site else []).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def render():
    st.set_page_config(
        page_title="Pharma KPI Platform",
        page_icon="💊",
        layout="wide",
    )

    # ── Sidebar ────────────────────────────────────────────────────────────
    st.sidebar.title("💊 Pharma KPI")
    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigation", ["📊 Overview", "🏭 Site Detail", "🤖 Forecast", "🔔 Alerts"])
    days = st.sidebar.slider("Last N days", 7, 365, 30)
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<div style='font-size:12px;color:#888'>"
        "🔗 <a href='https://github.com/BadreddineEK/pharma-kpi-platform' target='_blank'>GitHub</a>"
        " · Built by <a href='https://github.com/BadreddineEK' target='_blank'>Badreddine EK</a>"
        "</div>",
        unsafe_allow_html=True,
    )

    df = load_data(days)

    # ══════════════════════════════════════════════════════════════════════
    if page == "📊 Overview":
        st.title("📊 KPI Overview")
        st.caption(f"Last {days} days — all sites")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Batch Yield", f"{df['batch_yield'].mean():.1f}%",
                  delta=f"{df['batch_yield'].mean()-95:.1f}% vs target")
        c2.metric("Avg Cycle Time", f"{df['cycle_time'].mean():.1f}h",
                  delta=f"{df['cycle_time'].mean()-36:.1f}h vs target", delta_color="inverse")
        c3.metric("Avg OOS Rate", f"{df['oos_rate'].mean():.2f}%",
                  delta=f"{df['oos_rate'].mean()-1.2:.2f}% vs target", delta_color="inverse")
        c4.metric("Revenue Index", f"{df['revenue_index'].mean():.1f}")

        st.markdown("---")

        daily = df.groupby("date")["batch_yield"].mean().reset_index()
        fig = px.line(daily, x="date", y="batch_yield", title="Daily avg Batch Yield (all sites)")
        fig.add_hline(y=92, line_dash="dash", line_color="red", annotation_text="Min 92%")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.box(df, x="site", y="oos_rate", color="site", title="OOS Rate by site")
            fig2.add_hline(y=2, line_dash="dash", line_color="orange")
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            fig3 = px.box(df, x="site", y="cycle_time", color="site", title="Cycle Time by site")
            fig3.add_hline(y=48, line_dash="dash", line_color="orange")
            st.plotly_chart(fig3, use_container_width=True)

        with st.expander("📋 Raw data"):
            st.dataframe(df.head(300), use_container_width=True)
            st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(), "kpis.csv", "text/csv")

    # ══════════════════════════════════════════════════════════════════════
    elif page == "🏭 Site Detail":
        st.title("🏭 Site Detail")
        sites = sorted(df["site"].unique().tolist())
        site = st.selectbox("Site", sites)
        dfs = df[df["site"] == site]

        c1, c2, c3 = st.columns(3)
        c1.metric("Batch Yield", f"{dfs['batch_yield'].mean():.1f}%")
        c2.metric("Cycle Time", f"{dfs['cycle_time'].mean():.1f}h")
        c3.metric("OOS Rate", f"{dfs['oos_rate'].mean():.2f}%")

        metric = st.selectbox("Metric", ["batch_yield", "cycle_time", "oos_rate", "revenue_index", "adverse_events"])
        fig = px.line(dfs, x="date", y=metric, title=f"{metric.replace('_',' ').title()} — {site}")
        if metric in THRESHOLDS:
            op, val = THRESHOLDS[metric]
            fig.add_hline(y=val, line_dash="dash", line_color="red", annotation_text=f"Threshold {val}")
        st.plotly_chart(fig, use_container_width=True)

        dfs["week"] = dfs["date"].dt.strftime("W%W")
        breach_by_week = dfs.groupby("week").apply(
            lambda x: pd.Series({
                "batch_yield_breach": (x["batch_yield"] < 92).sum(),
                "oos_rate_breach": (x["oos_rate"] > 2).sum(),
                "cycle_time_breach": (x["cycle_time"] > 48).sum(),
            })
        ).reset_index()
        st.subheader("Weekly breach count")
        st.bar_chart(breach_by_week.set_index("week"))

    # ══════════════════════════════════════════════════════════════════════
    elif page == "🤖 Forecast":
        st.title("🤖 Forecast")
        st.caption("Linear trend + weekly seasonality — 30-day horizon")

        metric = st.selectbox("Metric", ["batch_yield", "cycle_time", "oos_rate", "revenue_index"])
        horizon = st.slider("Horizon (days)", 7, 60, 30)

        hist = df.groupby("date")[metric].mean().reset_index()
        hist.columns = ["ds", "y"]

        if len(hist) < 14:
            st.warning("Not enough data.")
        else:
            from sklearn.linear_model import LinearRegression
            hist["t"] = (hist["ds"] - hist["ds"].min()).dt.days
            hist["dow"] = hist["ds"].dt.dayofweek
            dow_dummies = pd.get_dummies(hist["dow"], prefix="dow")
            X = pd.concat([hist[["t"]], dow_dummies], axis=1)
            model = LinearRegression().fit(X, hist["y"])

            last_t = int(hist["t"].max())
            last_date = hist["ds"].max()
            future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon)
            future_t = np.arange(last_t + 1, last_t + 1 + horizon)
            future_dow = future_dates.dayofweek
            X_fut = pd.DataFrame({"t": future_t})
            for i in range(7):
                X_fut[f"dow_{i}"] = (future_dow == i).astype(int)
            for col in X.columns:
                if col not in X_fut.columns:
                    X_fut[col] = 0
            X_fut = X_fut[X.columns]
            yhat = model.predict(X_fut)
            resid_std = float(np.std(hist["y"].values - model.predict(X)))

            forecast = pd.DataFrame({"ds": future_dates, "yhat": yhat,
                                      "lo": yhat - 1.96*resid_std, "hi": yhat + 1.96*resid_std})

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist["ds"], y=hist["y"], name="Historical", line=dict(color="#4C9BE8")))
            fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"], name="Forecast", line=dict(color="#F4A261", dash="dash")))
            fig.add_trace(go.Scatter(
                x=list(forecast["ds"]) + list(forecast["ds"][::-1]),
                y=list(forecast["hi"]) + list(forecast["lo"][::-1]),
                fill="toself", fillcolor="rgba(244,162,97,0.15)",
                line=dict(color="rgba(0,0,0,0)"), name="95% CI"
            ))
            if metric in THRESHOLDS:
                op, val = THRESHOLDS[metric]
                fig.add_hline(y=val, line_dash="dot", line_color="red", annotation_text=f"Threshold {val}")
            fig.update_layout(title=f"{metric.replace('_',' ').title()} — {horizon}d forecast", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════
    elif page == "🔔 Alerts":
        st.title("🔔 Alert Events")
        st.caption(f"KPI breaches — last {days} days")

        events = []
        checks = [
            ("batch_yield", "lt", 92.0),
            ("oos_rate", "gt", 2.0),
            ("cycle_time", "gt", 48.0),
            ("adverse_events", "gt", 5.0),
        ]
        for metric, op, thresh in checks:
            mask = df[metric] < thresh if op == "lt" else df[metric] > thresh
            breached = df[mask][["date", "site", metric]].copy()
            breached["metric"] = metric
            breached["value"] = breached[metric].round(2)
            breached["threshold"] = thresh
            events.append(breached[["date", "site", "metric", "value", "threshold"]])

        alerts_df = pd.concat(events).sort_values("date", ascending=False).reset_index(drop=True)

        if alerts_df.empty:
            st.success("✅ No breaches in this window!")
        else:
            st.error(f"🚨 {len(alerts_df)} breach events")
            st.dataframe(alerts_df, use_container_width=True)
            fig = px.histogram(alerts_df, x="metric", color="site", title="Breaches by metric & site")
            st.plotly_chart(fig, use_container_width=True)
