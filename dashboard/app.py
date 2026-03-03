"""Streamlit dashboard entry point."""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Pharma KPI Platform",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar navigation ─────────────────────────────────────────────────────────
st.sidebar.title("💊 Pharma KPI")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📊 Overview", "🏭 Site Detail", "🤖 Forecasts", "🔔 Alerts"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Data window**")
days = st.sidebar.slider("Last N days", min_value=7, max_value=365, value=30)

# ── Page routing ───────────────────────────────────────────────────────────────
if page == "📊 Overview":
    from dashboard.pages.overview import render
    render(days=days)
elif page == "🏭 Site Detail":
    from dashboard.pages.site_detail import render
    render(days=days)
elif page == "🤖 Forecasts":
    from dashboard.pages.forecasts import render
    render()
else:
    from dashboard.pages.alerts_page import render
    render(days=days)
