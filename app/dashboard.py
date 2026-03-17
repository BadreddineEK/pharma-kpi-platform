"""Pharma KPI Platform — main Streamlit dashboard.

Business context
----------------
Pharmaceutical manufacturing is one of the most regulated industries in the world.
Every batch produced must comply with strict GMP (Good Manufacturing Practice)
thresholds defined by EMA / FDA. A single breach can trigger a regulatory hold,
a product recall, or financial penalties.

This platform simulates the real-time KPI monitoring dashboard a Data / Quality
Engineering team would maintain across a multi-site manufacturing network. It
covers five core areas: network-wide overview, per-site drill-down, ML-based
forecasting, alert management, and cross-site KPI comparison.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

# ── DB path ──────────────────────────────────────────────────────────────────
_default_db = str(Path(tempfile.gettempdir()) / "kpis.db")
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", _default_db)

# ── KPI catalogue ─────────────────────────────────────────────────────────────
METRICS: dict[str, dict] = {
    "batch_yield": dict(
        label="Batch Yield", unit="%", direction="lt", threshold=92.0,
        good="#00A878", bad="#E63946",
        description=(
            "Percentage of a batch that meets quality specifications. "
            "Below 92 % triggers a GMP non-conformance review under 21 CFR Part 211."
        ),
    ),
    "cycle_time": dict(
        label="Cycle Time", unit="h", direction="gt", threshold=48.0,
        good="#00A878", bad="#F4A261",
        description=(
            "End-to-end manufacturing time per batch (hours). "
            "Above 48 h indicates process inefficiency, equipment downtime, or scheduling drift."
        ),
    ),
    "oos_rate": dict(
        label="OOS Rate", unit="%", direction="gt", threshold=2.0,
        good="#00A878", bad="#E63946",
        description=(
            "Out-of-Specification rate — % of quality tests failing release criteria. "
            "Above 2 % requires a formal CAPA investigation per ICH Q10."
        ),
    ),
    "adverse_events": dict(
        label="Adverse Events", unit="", direction="gt", threshold=5.0,
        good="#00A878", bad="#E63946",
        description=(
            "Count of reportable adverse events in the clinical / post-market context. "
            "Above 5 triggers a pharmacovigilance review under EMA guidelines."
        ),
    ),
    "revenue_index": dict(
        label="Revenue Index", unit="", direction=None, threshold=None,
        good="#4C9BE8", bad="#4C9BE8",
        description=(
            "Indexed revenue performance (base = 100). "
            "Tracks the financial impact of quality events and process improvements."
        ),
    ),
    "trials_enrolled": dict(
        label="Trials Enrolled", unit="", direction=None, threshold=None,
        good="#4C9BE8", bad="#4C9BE8",
        description="Number of patients enrolled in active clinical trials at this site.",
    ),
}

SITE_COLORS = {
    "Lyon": "#4C9BE8",
    "Paris": "#F4A261",
    "Strasbourg": "#00A878",
    "Bordeaux": "#E63946",
}

REGULATED_METRICS = [k for k, v in METRICS.items() if v["direction"] is not None]
ALL_METRIC_KEYS   = list(METRICS.keys())


# ── Data helpers ──────────────────────────────────────────────────────────────

def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DUCKDB_PATH)


@st.cache_data(ttl=300, show_spinner=False)
def load_data(days: int, site: str | None = None) -> pd.DataFrame:
    """Load KPI records from DuckDB for the given rolling window."""
    con = _get_con()
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


def compliance_rate(series: pd.Series, direction: str, threshold: float) -> float:
    if direction == "lt":
        return float((series >= threshold).mean())
    return float((series <= threshold).mean())


def breach_mask(series: pd.Series, direction: str, threshold: float) -> pd.Series:
    if direction == "lt":
        return series < threshold
    return series > threshold


def deviation_pct(value: float, threshold: float) -> float:
    return (value - threshold) / threshold * 100


def severity_label(dev: float, direction: str) -> str:
    sign = -1 if direction == "lt" else 1
    return "Critical" if sign * dev > 10 else "Warning"


# ── UI helpers ─────────────────────────────────────────────────────────────────

def _compliance_badge(rate: float) -> str:
    if rate >= 0.95:
        color, label = "#00A878", "Compliant"
    elif rate >= 0.85:
        color, label = "#F4A261", "At Risk"
    else:
        color, label = "#E63946", "Breaching"
    return (
        f"<span style='background:{color};color:#fff;padding:2px 8px;"
        f"border-radius:8px;font-size:11px;font-weight:600'>{label}</span>"
    )


def _metric_card(col, label: str, value: str, delta: str,
                 delta_inverse: bool, compliance: float | None = None):
    with col:
        st.metric(label=label, value=value, delta=delta,
                  delta_color="inverse" if delta_inverse else "normal")
        if compliance is not None:
            st.markdown(
                f"{_compliance_badge(compliance)}"
                f"<span style='font-size:11px;color:#888;margin-left:6px'>"
                f"{compliance * 100:.0f}% compliant</span>",
                unsafe_allow_html=True,
            )


def _chart_theme(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color="#FAFAFA"), x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CCCCCC", size=12),
        legend=dict(
            bgcolor="rgba(255,255,255,0.05)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1,
        ),
        xaxis=dict(gridcolor="rgba(255,255,255,0.07)", showline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.07)", showline=False),
        margin=dict(t=45, b=30, l=10, r=10),
        hovermode="x unified",
    )
    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_sidebar() -> tuple[str, int]:
    with st.sidebar:
        st.markdown(
            "<h2 style='margin-bottom:0'>💊 Pharma KPI</h2>"
            "<p style='color:#888;font-size:13px;margin-top:4px'>"
            "Manufacturing Intelligence Platform</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        page = st.radio(
            "📋 **Navigation**",
            ["🏠 Overview", "🔬 Site Detail", "📈 Forecast", "🚨 Alerts", "📊 KPI Comparison"],
        )

        st.markdown("---")
        st.markdown("**⚙️ Filters**")
        days = st.slider(
            "Time window (days)", 7, 365, 90,
            help="All charts and metrics reflect this rolling window.",
        )

        st.markdown("---")
        with st.expander("ℹ️ About this platform", expanded=False):
            st.markdown(
                """
**What it does**
Real-time KPI monitoring across a 4-site pharmaceutical manufacturing
network — the kind of tool a Data Engineering team maintains to ensure
GMP compliance and detect quality drifts before they escalate.

**Data**
365 days × 4 sites of synthetic data generated with realistic
site-specific baselines, incident windows, and continuous-improvement
trends. Stored in an in-process **DuckDB** columnar database.

**KPI thresholds (EMA/FDA-aligned)**
| KPI | Threshold |
|---|---|
| Batch Yield | ≥ 92 % |
| Cycle Time | ≤ 48 h |
| OOS Rate | ≤ 2 % |
| Adverse Events | ≤ 5 |

**Stack** — Python 3.11 · Streamlit · DuckDB · Plotly · scikit-learn
                """
            )

        st.markdown("---")
        st.markdown(
            "<div style='font-size:11px;color:#555;line-height:1.8'>"
            "Built by <a href='https://github.com/BadreddineEK' style='color:#00A878' target='_blank'>"
            "Badreddine EK</a><br>"
            "<a href='https://github.com/BadreddineEK/pharma-kpi-platform' "
            "style='color:#555' target='_blank'>GitHub ↗</a>"
            "</div>",
            unsafe_allow_html=True,
        )

    return page.split(" ", 1)[1], days


# ── Page: Overview ────────────────────────────────────────────────────────────

def _page_overview(df: pd.DataFrame, days: int) -> None:
    st.title("🏠 Manufacturing KPI Overview")
    st.markdown(
        f"Network-wide performance across **{df['site'].nunique()} sites** "
        f"— last **{days} days** · {len(df):,} records"
    )

    c1, c2, c3, c4 = st.columns(4)
    _metric_card(
        c1, "Avg Batch Yield", f"{df['batch_yield'].mean():.1f} %",
        f"{df['batch_yield'].mean() - 95:+.1f}% vs target 95%", False,
        compliance_rate(df["batch_yield"], "lt", 92),
    )
    _metric_card(
        c2, "Avg Cycle Time", f"{df['cycle_time'].mean():.1f} h",
        f"{df['cycle_time'].mean() - 36:+.1f}h vs target 36h", True,
        compliance_rate(df["cycle_time"], "gt", 48),
    )
    _metric_card(
        c3, "Avg OOS Rate", f"{df['oos_rate'].mean():.2f} %",
        f"{df['oos_rate'].mean() - 1.2:+.2f}% vs target 1.2%", True,
        compliance_rate(df["oos_rate"], "gt", 2),
    )
    _metric_card(
        c4, "Revenue Index", f"{df['revenue_index'].mean():.1f}",
        f"{df['revenue_index'].mean() - 100:+.1f} vs base 100", False,
    )

    st.markdown("---")

    st.subheader("Site Compliance Matrix")
    st.caption("% of daily records within regulatory threshold — per site & KPI")

    hm_rows = []
    for site in sorted(df["site"].unique()):
        row = {"Site": site}
        for key in REGULATED_METRICS:
            m = METRICS[key]
            row[m["label"]] = round(
                compliance_rate(df[df["site"] == site][key], m["direction"], m["threshold"]) * 100, 1
            )
        hm_rows.append(row)
    hm_df = pd.DataFrame(hm_rows).set_index("Site")

    fig_hm = go.Figure(go.Heatmap(
        z=hm_df.values,
        x=hm_df.columns.tolist(),
        y=hm_df.index.tolist(),
        colorscale=[[0, "#E63946"], [0.85, "#F4A261"], [1.0, "#00A878"]],
        zmin=70, zmax=100,
        text=[[f"{v:.0f}%" for v in row] for row in hm_df.values],
        texttemplate="%{text}",
        hovertemplate="%{y} — %{x}: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="Compliance %", ticksuffix="%"),
    ))
    _chart_theme(fig_hm, "Compliance Rate (%) by Site & KPI")
    st.plotly_chart(fig_hm, use_container_width=True)

    st.subheader("Daily Trend — Batch Yield (7-day rolling avg)")
    daily = (
        df.groupby(["date", "site"])["batch_yield"]
        .mean().reset_index().sort_values("date")
    )
    daily["rolling"] = daily.groupby("site")["batch_yield"].transform(
        lambda s: s.rolling(7, min_periods=1).mean()
    )
    fig_trend = go.Figure()
    for site in sorted(daily["site"].unique()):
        sd = daily[daily["site"] == site]
        fig_trend.add_trace(go.Scatter(
            x=sd["date"], y=sd["rolling"], name=site,
            line=dict(color=SITE_COLORS.get(site, "#888"), width=2),
            hovertemplate=f"<b>{site}</b><br>%{{x|%d %b}}: %{{y:.1f}}%<extra></extra>",
        ))
    fig_trend.add_hline(
        y=92, line_dash="dot", line_color="#E63946",
        annotation_text="Min 92%", annotation_position="bottom right",
    )
    _chart_theme(fig_trend, "7-day rolling avg Batch Yield by site")
    fig_trend.update_yaxes(title_text="Batch Yield (%)")
    st.plotly_chart(fig_trend, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_oos = px.box(df, x="site", y="oos_rate", color="site",
                         color_discrete_map=SITE_COLORS, points="outliers")
        fig_oos.add_hline(y=2, line_dash="dot", line_color="#F4A261",
                          annotation_text="Max 2%")
        _chart_theme(fig_oos, "OOS Rate distribution by site")
        fig_oos.update_layout(showlegend=False)
        fig_oos.update_yaxes(title_text="OOS Rate (%)")
        st.plotly_chart(fig_oos, use_container_width=True)
    with col2:
        fig_ct = px.box(df, x="site", y="cycle_time", color="site",
                        color_discrete_map=SITE_COLORS, points="outliers")
        fig_ct.add_hline(y=48, line_dash="dot", line_color="#F4A261",
                         annotation_text="Max 48h")
        _chart_theme(fig_ct, "Cycle Time distribution by site")
        fig_ct.update_layout(showlegend=False)
        fig_ct.update_yaxes(title_text="Cycle Time (h)")
        st.plotly_chart(fig_ct, use_container_width=True)

    rev = df.groupby(["date", "site"])["revenue_index"].mean().reset_index()
    fig_rev = px.area(rev, x="date", y="revenue_index", color="site",
                      color_discrete_map=SITE_COLORS, line_group="site")
    fig_rev.add_hline(y=100, line_dash="dot", line_color="#888",
                      annotation_text="Base 100")
    _chart_theme(fig_rev, "Revenue Index over time by site")
    fig_rev.update_yaxes(title_text="Revenue Index")
    st.plotly_chart(fig_rev, use_container_width=True)

    with st.expander("📄 Raw data export"):
        st.dataframe(
            df.rename(columns={k: v["label"] for k, v in METRICS.items()})
              .sort_values(["date", "site"], ascending=[False, True])
              .head(500),
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Download full CSV",
            df.to_csv(index=False).encode(),
            file_name=f"pharma_kpis_last{days}d.csv",
            mime="text/csv",
        )


# ── Page: Site Detail ─────────────────────────────────────────────────────────

def _page_site_detail(df: pd.DataFrame, days: int) -> None:
    st.title("🔬 Site Detail")

    site = st.selectbox("Select site", sorted(df["site"].unique()),
                        format_func=lambda s: f"🏭 {s}")
    dfs  = df[df["site"] == site].sort_values("date").copy()
    st.markdown(
        f"**{site}** · {len(dfs):,} daily records · "
        f"{dfs['date'].min().strftime('%d %b %Y')} → "
        f"{dfs['date'].max().strftime('%d %b %Y')}"
    )

    c1, c2, c3, c4 = st.columns(4)
    for col, key in zip([c1, c2, c3, c4],
                        ["batch_yield", "cycle_time", "oos_rate", "adverse_events"]):
        m  = METRICS[key]
        val = dfs[key].mean()
        cr  = compliance_rate(dfs[key], m["direction"], m["threshold"])
        _metric_card(
            col, m["label"], f"{val:.2f}{m['unit']}",
            f"{val - m['threshold']:+.2f}{m['unit']} vs {m['threshold']}{m['unit']}",
            m["direction"] == "gt", cr,
        )

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📉 Trend", "📅 Breach Calendar", "🕸️ Site Profile"])

    with tab1:
        metric_key = st.selectbox("Metric", ALL_METRIC_KEYS,
                                  format_func=lambda k: METRICS[k]["label"])
        m    = METRICS[metric_key]
        roll = st.toggle("Show 7-day rolling average", value=True)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dfs["date"], y=dfs[metric_key], name="Daily",
            mode="lines",
            line=dict(color=SITE_COLORS.get(site, "#4C9BE8"), width=1.5),
            opacity=0.45,
        ))
        if roll:
            fig.add_trace(go.Scatter(
                x=dfs["date"],
                y=dfs[metric_key].rolling(7, min_periods=1).mean(),
                name="7-day avg",
                line=dict(color=SITE_COLORS.get(site, "#4C9BE8"), width=3),
            ))
        if m["direction"]:
            th_color = "#E63946" if m["direction"] == "gt" else "#F4A261"
            label    = f"Max {m['threshold']}{m['unit']}" if m["direction"] == "gt" else f"Min {m['threshold']}{m['unit']}"
            fig.add_hline(y=m["threshold"], line_dash="dot",
                          line_color=th_color, annotation_text=label,
                          annotation_position="top right")
        _chart_theme(fig, f"{m['label']} — {site}")
        ylabel = f"{m['label']} ({m['unit']})" if m["unit"] else m["label"]
        fig.update_yaxes(title_text=ylabel)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"ℹ️ {m['description']}")

    with tab2:
        st.markdown("Weekly count of days where a KPI exceeded its regulatory threshold.")
        dfs["week"] = dfs["date"].dt.to_period("W").apply(
            lambda r: str(r.start_time.date())
        )
        breach_data = (
            dfs.groupby("week")
            .apply(
                lambda x: pd.Series({
                    METRICS["batch_yield"]["label"]:    (x["batch_yield"] < 92).sum(),
                    METRICS["oos_rate"]["label"]:       (x["oos_rate"] > 2).sum(),
                    METRICS["cycle_time"]["label"]:     (x["cycle_time"] > 48).sum(),
                    METRICS["adverse_events"]["label"]: (x["adverse_events"] > 5).sum(),
                }),
                include_groups=False,
            )
            .reset_index()
        )
        fig_b = px.bar(
            breach_data.melt(id_vars="week", var_name="KPI", value_name="Breach Days"),
            x="week", y="Breach Days", color="KPI",
            color_discrete_sequence=["#E63946", "#F4A261", "#4C9BE8", "#A8DADC"],
            barmode="stack",
        )
        _chart_theme(fig_b, f"Weekly breach days — {site}")
        fig_b.update_xaxes(title_text="Week starting", tickangle=-45)
        fig_b.update_yaxes(title_text="Days in breach")
        st.plotly_chart(fig_b, use_container_width=True)

    with tab3:
        st.markdown(
            "Normalised compliance score per KPI (100 = fully compliant). "
            "Quickly identifies which KPIs are dragging site performance."
        )
        keys   = REGULATED_METRICS
        labels = [METRICS[k]["label"] for k in keys]
        vals   = [
            compliance_rate(dfs[k], METRICS[k]["direction"], METRICS[k]["threshold"]) * 100
            for k in keys
        ]
        sc = SITE_COLORS.get(site, "#4C9BE8")
        r, g, b = int(sc[1:3], 16), int(sc[3:5], 16), int(sc[5:7], 16)
        fig_r = go.Figure(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself",
            fillcolor=f"rgba({r},{g},{b},0.25)",
            line=dict(color=sc, width=2),
            name=site,
        ))
        fig_r.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%",
                                gridcolor="rgba(255,255,255,0.1)"),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CCCCCC"),
            showlegend=False,
            margin=dict(t=40, b=40),
        )
        _chart_theme(fig_r, f"KPI Compliance Profile — {site}")
        st.plotly_chart(fig_r, use_container_width=True)


# ── Page: Forecast ────────────────────────────────────────────────────────────

def _page_forecast(df: pd.DataFrame, days: int) -> None:
    st.title("📈 KPI Forecasting")
    st.markdown(
        "**Linear regression with day-of-week seasonality** trained on all 365 days of history. "
        "The shaded band is the **95 % prediction interval** (±1.96 σ of training residuals). "
        "Model coefficients and fit metrics are shown below."
    )

    col_l, col_r = st.columns([1, 2])
    with col_l:
        metric_key = st.selectbox(
            "KPI to forecast",
            [k for k in ALL_METRIC_KEYS if k != "trials_enrolled"],
            format_func=lambda k: METRICS[k]["label"],
        )
        horizon = st.slider("Forecast horizon (days)", 7, 90, 30)
        scope   = st.radio("Scope", ["All sites (average)", *sorted(df["site"].unique())])

    m = METRICS[metric_key]
    if scope == "All sites (average)":
        hist = df.groupby("date")[metric_key].mean().reset_index()
    else:
        hist = df[df["site"] == scope].groupby("date")[metric_key].mean().reset_index()
    hist.columns = ["ds", "y"]
    hist = hist.sort_values("ds").reset_index(drop=True)

    if len(hist) < 14:
        st.warning("Not enough data. Extend the time window to ≥ 14 days.")
        return

    hist["t"]   = (hist["ds"] - hist["ds"].min()).dt.days
    hist["dow"] = hist["ds"].dt.dayofweek
    dow_d  = pd.get_dummies(hist["dow"], prefix="dow", dtype=int)
    X_train = pd.concat([hist[["t"]], dow_d], axis=1)
    y_train = hist["y"]

    model    = LinearRegression().fit(X_train, y_train)
    y_pred   = model.predict(X_train)
    resid    = y_train.values - y_pred
    resid_std = float(np.std(resid))
    r2   = float(1 - np.var(resid) / np.var(y_train))
    rmse = float(np.sqrt(mean_squared_error(y_train, y_pred)))
    mae  = float(mean_absolute_error(y_train, y_pred))
    trend_coef = float(model.coef_[0])

    last_t    = int(hist["t"].max())
    last_date = hist["ds"].max()
    fut_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon)
    fut_t     = np.arange(last_t + 1, last_t + 1 + horizon)
    X_fut = pd.DataFrame({"t": fut_t})
    for i in range(7):
        X_fut[f"dow_{i}"] = (fut_dates.dayofweek == i).astype(int)
    for col in X_train.columns:
        if col not in X_fut.columns:
            X_fut[col] = 0
    X_fut = X_fut[X_train.columns]
    yhat  = model.predict(X_fut)

    forecast = pd.DataFrame({
        "ds":   fut_dates,
        "yhat": yhat,
        "lo":   yhat - 1.96 * resid_std,
        "hi":   yhat + 1.96 * resid_std,
    })

    with col_r:
        sc = SITE_COLORS.get(scope, "#4C9BE8") if scope != "All sites (average)" else "#4C9BE8"
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist["ds"], y=hist["y"], name="Historical",
            line=dict(color=sc, width=2),
            hovertemplate=f"%{{x|%d %b}}: %{{y:.2f}}{m['unit']}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=list(forecast["ds"]) + list(forecast["ds"][::-1]),
            y=list(forecast["hi"]) + list(forecast["lo"][::-1]),
            fill="toself", fillcolor="rgba(244,162,97,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="95% Prediction Interval", hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=forecast["ds"], y=forecast["yhat"], name="Forecast",
            line=dict(color="#F4A261", width=2.5, dash="dash"),
            hovertemplate=f"Forecast %{{x|%d %b}}: %{{y:.2f}}{m['unit']}<extra></extra>",
        ))
        if m["direction"]:
            th_c   = "#E63946" if m["direction"] == "gt" else "#F4A261"
            th_lbl = f"Max {m['threshold']}{m['unit']}" if m["direction"] == "gt" else f"Min {m['threshold']}{m['unit']}"
            fig.add_hline(y=m["threshold"], line_dash="dot",
                          line_color=th_c, annotation_text=th_lbl)
        _chart_theme(fig, f"{m['label']} — {horizon}-day forecast ({scope})")
        ylabel = f"{m['label']} ({m['unit']})" if m["unit"] else m["label"]
        fig.update_yaxes(title_text=ylabel)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 🤖 Model Performance")
    trend_dir = (
        "↑ improving"
        if (metric_key == "batch_yield" and trend_coef > 0)
        or (metric_key not in ("batch_yield", "revenue_index") and trend_coef < 0)
        else ("↓ degrading" if trend_coef != 0 else "→ stable")
    )
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("R²",    f"{r2:.3f}",   help="Coefficient of determination — 1 = perfect fit")
    mc2.metric("RMSE",  f"{rmse:.3f}", help="Root Mean Square Error (same unit as KPI)")
    mc3.metric("MAE",   f"{mae:.3f}",  help="Mean Absolute Error — average prediction error")
    mc4.metric("Trend", trend_dir,     help=f"Linear coefficient: {trend_coef:+.4f}/day")

    with st.expander("📐 Model details"):
        st.markdown(
            f"**Algorithm** : Ordinary Least Squares (scikit-learn `LinearRegression`)  \n"
            f"**Features** : day index `t` (linear trend) + 6 one-hot day-of-week dummies (weekly seasonality)  \n"
            f"**Training observations** : {len(hist)}  \n"
            f"**Residual σ** : {resid_std:.3f} → 95 % CI = ±{1.96 * resid_std:.3f} {m['unit']}  \n"
            f"**Trend coefficient** : {trend_coef:+.4f} {m['unit']}/day"
        )


# ── Page: Alerts ──────────────────────────────────────────────────────────────

def _page_alerts(df: pd.DataFrame, days: int) -> None:
    st.title("🚨 Alert Management")
    st.markdown(
        f"Regulatory threshold breaches detected across all sites in the last **{days} days**. "
        "**Critical** = deviation > 10 % beyond threshold. "
        "**Warning** = deviation ≤ 10 %."
    )

    checks = [
        ("batch_yield",    "lt", 92.0),
        ("oos_rate",       "gt", 2.0),
        ("cycle_time",     "gt", 48.0),
        ("adverse_events", "gt", 5.0),
    ]
    events = []
    for key, op, thresh in checks:
        m    = METRICS[key]
        mask = breach_mask(df[key], op, thresh)
        b    = df[mask][["date", "site", key]].copy()
        b["KPI"]       = m["label"]
        b["Value"]     = b[key].round(3)
        b["Threshold"] = thresh
        b["Unit"]      = m["unit"]
        b["Dev %"]     = b[key].apply(lambda v: round(deviation_pct(v, thresh), 1))
        b["Severity"]  = b["Dev %"].apply(lambda d: severity_label(d, op))
        events.append(b[["date", "site", "KPI", "Value", "Unit", "Threshold", "Dev %", "Severity"]])

    if not events:
        st.success("✅ No KPI breaches detected in the selected window.")
        return

    alerts_df = (
        pd.concat(events)
        .sort_values(["Severity", "date"], ascending=[True, False])
        .reset_index(drop=True)
    )
    alerts_df["date"] = alerts_df["date"].dt.strftime("%Y-%m-%d")

    n_crit = (alerts_df["Severity"] == "Critical").sum()
    n_warn = (alerts_df["Severity"] == "Warning").sum()

    s1, s2, s3 = st.columns(3)
    s1.metric("🔴 Critical", n_crit, help="Deviation > 10 % beyond threshold")
    s2.metric("🟡 Warning",  n_warn, help="Deviation ≤ 10 % beyond threshold")
    s3.metric("📋 Total",    len(alerts_df))

    st.markdown("---")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sel_sev   = st.multiselect("Severity", ["Critical", "Warning"],
                                   default=["Critical", "Warning"])
    with col_f2:
        sel_sites = st.multiselect("Site", sorted(df["site"].unique()),
                                   default=sorted(df["site"].unique()))

    filtered = alerts_df[
        alerts_df["Severity"].isin(sel_sev) & alerts_df["site"].isin(sel_sites)
    ].rename(columns={"site": "Site", "date": "Date"})

    def _style_sev(val: str) -> str:
        return "color:#E63946;font-weight:600" if val == "Critical" else "color:#F4A261"

    st.dataframe(
        filtered.style.map(_style_sev, subset=["Severity"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    tl = (
        alerts_df
        .assign(date=pd.to_datetime(alerts_df["date"]))
        .groupby(["date", "KPI"])
        .size()
        .reset_index(name="count")
    )
    fig_tl = px.bar(
        tl, x="date", y="count", color="KPI",
        color_discrete_sequence=["#E63946", "#F4A261", "#4C9BE8", "#A8DADC"],
        barmode="stack",
    )
    _chart_theme(fig_tl, "Daily breach events by KPI")
    fig_tl.update_yaxes(title_text="Breach count")
    st.plotly_chart(fig_tl, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        by_site = alerts_df.groupby("site").size().reset_index(name="Breaches")
        fig_s   = px.bar(by_site, x="site", y="Breaches", color="site",
                         color_discrete_map=SITE_COLORS, text="Breaches")
        fig_s.update_traces(textposition="outside")
        _chart_theme(fig_s, "Total breaches by site")
        fig_s.update_layout(showlegend=False)
        st.plotly_chart(fig_s, use_container_width=True)
    with col_b:
        by_kpi = alerts_df.groupby("KPI").size().reset_index(name="Breaches")
        fig_k  = px.pie(by_kpi, names="KPI", values="Breaches",
                        color_discrete_sequence=["#E63946", "#F4A261", "#4C9BE8", "#A8DADC"],
                        hole=0.45)
        fig_k.update_traces(textposition="inside", textinfo="percent+label")
        _chart_theme(fig_k, "Breach share by KPI")
        st.plotly_chart(fig_k, use_container_width=True)


# ── Page: KPI Comparison ──────────────────────────────────────────────────────

def _page_kpi_comparison(df: pd.DataFrame, days: int) -> None:
    st.title("📊 KPI Comparison")
    st.markdown(
        f"Side-by-side benchmarking of all sites across regulated KPIs — last **{days} days**. "
        "Identify leaders and laggards at a glance."
    )

    # ── 1. KPI selector + grouped bar chart ──────────────────────────────────
    metric_key = st.selectbox(
        "Select KPI to compare",
        REGULATED_METRICS,
        format_func=lambda k: METRICS[k]["label"],
    )
    m = METRICS[metric_key]

    avg_by_site = (
        df.groupby("site")[metric_key]
        .mean()
        .reset_index()
        .rename(columns={metric_key: "avg"})
        .sort_values("avg", ascending=(m["direction"] != "lt"))
    )

    fig_bar = go.Figure()
    for _, row in avg_by_site.iterrows():
        site = row["site"]
        val  = row["avg"]
        is_breach = (
            (m["direction"] == "lt" and val < m["threshold"]) or
            (m["direction"] == "gt" and val > m["threshold"])
        ) if m["direction"] else False
        color = "#E63946" if is_breach else SITE_COLORS.get(site, "#4C9BE8")
        fig_bar.add_trace(go.Bar(
            x=[site], y=[val],
            name=site,
            marker_color=color,
            text=[f"{val:.2f}{m['unit']}"],
            textposition="outside",
            hovertemplate=f"<b>{site}</b><br>{m['label']}: %{{y:.2f}}{m['unit']}<extra></extra>",
        ))
    if m["direction"]:
        th_color = "#F4A261" if m["direction"] == "gt" else "#E63946"
        th_label = f"Threshold: {m['threshold']}{m['unit']}"
        fig_bar.add_hline(y=m["threshold"], line_dash="dot",
                          line_color=th_color, annotation_text=th_label,
                          annotation_position="top right")
    _chart_theme(fig_bar, f"Average {m['label']} by site — last {days} days")
    fig_bar.update_layout(showlegend=False, bargap=0.35)
    fig_bar.update_yaxes(title_text=f"{m['label']} ({m['unit']})" if m["unit"] else m["label"])
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── 2. Percentile ranking table across ALL regulated KPIs ─────────────────
    st.subheader("🏆 Site Ranking — All Regulated KPIs")
    st.caption(
        "Rank 1 = best performer. Green = compliant average, Red = non-compliant average."
    )

    rank_rows = []
    for site in sorted(df["site"].unique()):
        row = {"Site": site}
        dfs = df[df["site"] == site]
        for key in REGULATED_METRICS:
            mm  = METRICS[key]
            avg = dfs[key].mean()
            cr  = compliance_rate(dfs[key], mm["direction"], mm["threshold"]) * 100
            row[mm["label"]] = f"{avg:.2f}{mm['unit']} ({cr:.0f}%)"
        rank_rows.append(row)
    rank_df = pd.DataFrame(rank_rows).set_index("Site")
    st.dataframe(rank_df, use_container_width=True)

    st.markdown("---")

    # ── 3. Delta heatmap: deviation from network average ─────────────────────
    st.subheader("📐 Site Delta vs Network Average")
    st.caption(
        "Each cell shows how much a site deviates from the network mean for that KPI. "
        "Red = worse than average, Green = better than average."
    )

    delta_rows = []
    net_avgs = {key: df[key].mean() for key in REGULATED_METRICS}
    for site in sorted(df["site"].unique()):
        row = {"Site": site}
        dfs = df[df["site"] == site]
        for key in REGULATED_METRICS:
            mm  = METRICS[key]
            site_avg = dfs[key].mean()
            delta    = site_avg - net_avgs[key]
            row[mm["label"]] = round(delta, 3)
        delta_rows.append(row)
    delta_df = pd.DataFrame(delta_rows).set_index("Site")

    # For regulated KPIs: green = lower is better for cycle_time/oos_rate/adverse_events
    # For batch_yield: green = higher is better
    # We flip the colorscale for "lt" direction KPIs
    fig_delta = go.Figure(go.Heatmap(
        z=delta_df.values,
        x=delta_df.columns.tolist(),
        y=delta_df.index.tolist(),
        colorscale=[[0, "#00A878"], [0.5, "rgba(255,255,255,0.05)"], [1.0, "#E63946"]],
        text=[[f"{v:+.2f}" for v in row] for row in delta_df.values],
        texttemplate="%{text}",
        hovertemplate="%{y} — %{x}: %{z:+.3f}<extra></extra>",
        colorbar=dict(title="Δ vs avg"),
        zmid=0,
    ))
    _chart_theme(fig_delta, "Site deviation from network average (per KPI)")
    st.plotly_chart(fig_delta, use_container_width=True)
    st.caption(
        "⚠️ Note: for Cycle Time, OOS Rate and Adverse Events, "
        "a *negative* delta (green) means the site is performing **better** than average. "
        "For Batch Yield, a *positive* delta (red) means better-than-average yield."
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def render() -> None:
    st.set_page_config(
        page_title="Pharma KPI Platform",
        page_icon="💊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/BadreddineEK/pharma-kpi-platform",
            "Report a bug": "https://github.com/BadreddineEK/pharma-kpi-platform/issues",
            "About": "Pharma KPI Platform — manufacturing intelligence dashboard by Badreddine EK.",
        },
    )

    page, days = _render_sidebar()
    df = load_data(days)

    if df.empty:
        st.error("No data found. Restart the app to re-seed the database.")
        return

    if page == "Overview":
        _page_overview(df, days)
    elif page == "Site Detail":
        _page_site_detail(df, days)
    elif page == "Forecast":
        _page_forecast(df, days)
    elif page == "Alerts":
        _page_alerts(df, days)
    elif page == "KPI Comparison":
        _page_kpi_comparison(df, days)
