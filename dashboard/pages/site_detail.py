"""Site detail page — drill-down per manufacturing site."""

import plotly.express as px
import streamlit as st

from pipeline.load import get_connection


def render(days: int = 30) -> None:
    st.title("🏭 Site Detail")

    con = get_connection()
    sites = con.execute("SELECT DISTINCT site FROM kpis ORDER BY site").df()["site"].tolist()
    con.close()

    if not sites:
        st.warning("No data available. Run the pipeline first.")
        return

    selected_site = st.selectbox("Select site", sites)

    con = get_connection()
    df = con.execute(f"""
        SELECT * FROM kpis
        WHERE site = ? AND date >= current_date - INTERVAL '{days} days'
        ORDER BY date
    """, [selected_site]).df()
    con.close()

    if df.empty:
        st.warning(f"No data for site {selected_site} in the last {days} days.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Batch Yield", f"{df['batch_yield'].mean():.1f}%")
    col2.metric("Cycle Time", f"{df['cycle_time'].mean():.1f}h")
    col3.metric("OOS Rate", f"{df['oos_rate'].mean():.2f}%")

    metrics = ["batch_yield", "cycle_time", "oos_rate", "revenue_index", "adverse_events"]
    selected_metric = st.selectbox("Metric to visualise", metrics)

    fig = px.line(df, x="date", y=selected_metric,
                  title=f"{selected_metric.replace('_', ' ').title()} — {selected_site}")
    st.plotly_chart(fig, use_container_width=True)

    # Breach heatmap by week
    df["week_label"] = df["date"].dt.strftime("W%W")
    breach_summary = df.groupby("week_label")[["batch_yield_breach", "oos_rate_breach"]].sum()
    st.subheader("Weekly Breach Count")
    st.bar_chart(breach_summary)
