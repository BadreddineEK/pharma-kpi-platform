"""Alerts page — recent KPI breach events."""

import streamlit as st

from pipeline.load import get_connection


def render(days: int = 7) -> None:
    st.title("🔔 Alert Events")
    st.caption(f"KPI breaches in the last {days} days")

    con = get_connection()
    df = con.execute(f"""
        SELECT date, site, 'batch_yield' as metric, ROUND(batch_yield, 2) as value, 92.0 as threshold, 'lt' as operator
        FROM kpis WHERE batch_yield_breach = true AND date >= current_date - INTERVAL '{days} days'
        UNION ALL
        SELECT date, site, 'oos_rate', ROUND(oos_rate, 2), 2.0, 'gt'
        FROM kpis WHERE oos_rate_breach = true AND date >= current_date - INTERVAL '{days} days'
        UNION ALL
        SELECT date, site, 'cycle_time', ROUND(cycle_time, 2), 48.0, 'gt'
        FROM kpis WHERE cycle_time_breach = true AND date >= current_date - INTERVAL '{days} days'
        ORDER BY date DESC
    """).df()
    con.close()

    if df.empty:
        st.success("✅ No breaches in the selected window!")
        return

    st.error(f"🚨 {len(df)} breach events found")
    st.dataframe(
        df.style.applymap(lambda v: "background-color: #ff4b4b; color: white" if isinstance(v, str) and v in ["batch_yield", "oos_rate", "cycle_time"] else ""),
        use_container_width=True
    )

    import plotly.express as px
    fig = px.histogram(df, x="metric", color="site", title="Breach events by metric and site")
    st.plotly_chart(fig, use_container_width=True)
