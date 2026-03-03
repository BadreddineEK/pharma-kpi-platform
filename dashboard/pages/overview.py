"""Overview page — global KPI summary across all sites."""

import pandas as pd
import plotly.express as px
import streamlit as st

from pipeline.load import get_connection


def render(days: int = 30) -> None:
    st.title("📊 KPI Overview")
    st.caption(f"Showing last {days} days — all sites combined")

    con = get_connection()
    df = con.execute(f"""
        SELECT * FROM kpis
        WHERE date >= current_date - INTERVAL '{days} days'
        ORDER BY date DESC
    """).df()
    con.close()

    if df.empty:
        st.warning("⚠️ No data available. Run the pipeline first: `python -m pipeline.scheduler --run-once`")
        return

    # ── KPI Cards ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Batch Yield", f"{df['batch_yield'].mean():.1f}%",
                delta=f"{df['batch_yield'].mean() - 95:.1f}% vs target")
    col2.metric("Avg Cycle Time", f"{df['cycle_time'].mean():.1f}h",
                delta=f"{df['cycle_time'].mean() - 36:.1f}h vs target", delta_color="inverse")
    col3.metric("Avg OOS Rate", f"{df['oos_rate'].mean():.2f}%",
                delta=f"{df['oos_rate'].mean() - 1.2:.2f}% vs target", delta_color="inverse")
    col4.metric("Avg Revenue Index", f"{df['revenue_index'].mean():.1f}")

    st.markdown("---")

    # ── Breach summary ─────────────────────────────────────────────────────────
    total = len(df)
    breach_pct = df["batch_yield_breach"].sum() / total * 100
    st.markdown(f"🚨 **{df['batch_yield_breach'].sum()}** batch yield breaches in window ({breach_pct:.1f}%)")

    # ── Time series ────────────────────────────────────────────────────────────
    st.subheader("Batch Yield over time")
    daily = df.groupby("date")["batch_yield"].mean().reset_index()
    fig = px.line(daily, x="date", y="batch_yield", title="Daily avg batch yield (all sites)")
    fig.add_hline(y=92, line_dash="dash", line_color="red", annotation_text="Min threshold 92%")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("OOS Rate by Site")
    fig2 = px.box(df, x="site", y="oos_rate", color="site", title="OOS Rate distribution per site")
    fig2.add_hline(y=2, line_dash="dash", line_color="orange", annotation_text="Threshold 2%")
    st.plotly_chart(fig2, use_container_width=True)

    # ── Raw data table ─────────────────────────────────────────────────────────
    with st.expander("📋 Raw data"):
        st.dataframe(df.head(200), use_container_width=True)
        csv = df.to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", csv, "kpis_export.csv", "text/csv")
