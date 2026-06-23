"""FinanceOps executive dashboard — polished light theme, Plotly charts, sparklines."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from financeops.anomaly.detector import detect_all  # noqa: E402
from financeops.kpi.engine import (  # noqa: E402
    category_performance, compute_snapshot, daily_series, region_performance, revenue_trend,
)

ACCENT = "#4F46E5"
INK = "#0F172A"
MUTED = "#64748B"
GOOD = "#059669"
BAD = "#DC2626"
GRID = "#EEF1F6"
CAT_COLORS = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"]

st.set_page_config(page_title="FinanceOps", page_icon="📊", layout="wide")

st.markdown(f"""
<style>
  .stApp {{ background:#F6F7FB; }}
  #MainMenu, footer, header {{ visibility:hidden; }}
  .block-container {{ padding:1.5rem 2.5rem 3rem; max-width:1400px; }}
  h1,h2,h3,h4 {{ color:{INK}; letter-spacing:-.01em; }}
  .eyebrow {{ color:{MUTED}; font-size:12px; font-weight:700; text-transform:uppercase;
    letter-spacing:.08em; margin:26px 0 10px; }}
  .card {{ background:#fff; border:1px solid #E6E9F0; border-left:3px solid var(--bar,{ACCENT});
    border-radius:12px; padding:14px 16px; box-shadow:0 1px 2px rgba(16,24,40,.04); }}
  .card .lab {{ color:{MUTED}; font-size:11.5px; font-weight:700; text-transform:uppercase;
    letter-spacing:.05em; }}
  .card .val {{ color:{INK}; font-size:26px; font-weight:800; margin-top:2px; line-height:1.1; }}
  .card .dl {{ font-size:12px; font-weight:700; margin-top:3px; }}
  .alert {{ background:#fff; border:1px solid #E6E9F0; border-left:4px solid var(--c,{MUTED});
    border-radius:10px; padding:11px 14px; margin-bottom:8px;
    display:flex; justify-content:space-between; align-items:center; font-size:13.5px; }}
  .pill {{ padding:2px 9px; border-radius:999px; font-size:11px; font-weight:800; margin-right:8px; }}
  .sb-stat {{ display:flex; justify-content:space-between; padding:7px 0;
    border-bottom:1px solid #E6E9F0; font-size:13px; color:{INK}; }}
  .sb-stat b {{ color:{INK}; }}
</style>
""", unsafe_allow_html=True)


def fmt_money(v):
    if abs(v) >= 1e7: return f"Rs {v/1e7:.2f} Cr"
    if abs(v) >= 1e5: return f"Rs {v/1e5:.2f} L"
    if abs(v) >= 1e3: return f"Rs {v/1e3:.1f} K"
    return f"Rs {v:,.0f}"


def spark(values, color):
    pts = [float(v) for v in values]
    if len(pts) < 2:
        return ""
    mn, mx = min(pts), max(pts)
    rng = (mx - mn) or 1
    w, h = 120, 30
    step = w / (len(pts) - 1)
    coords = " ".join(f"{i*step:.1f},{h - (v-mn)/rng*h:.1f}" for i, v in enumerate(pts))
    return (f'<svg width="{w}" height="{h}" style="margin-top:6px;display:block">'
            f'<polyline points="{coords}" fill="none" stroke="{color}" '
            f'stroke-width="1.6" stroke-linejoin="round"/></svg>')


def card(col, label, value, bar=ACCENT, delta=None, good_up=True, series=None):
    dl = ""
    if delta is not None:
        up = delta >= 0
        ok = up if good_up else not up
        dl = f'<div class="dl" style="color:{GOOD if ok else BAD}">{"▲" if up else "▼"} {abs(delta):.1f}%</div>'
    sp = spark(series, bar) if series is not None else ""
    col.markdown(f'<div class="card" style="--bar:{bar}"><div class="lab">{label}</div>'
                 f'<div class="val">{value}</div>{dl}{sp}</div>', unsafe_allow_html=True)


@st.cache_data(ttl=300)
def get_snap(d): e = dt.date.today(); return compute_snapshot(e - dt.timedelta(days=d), e).to_dict()
@st.cache_data(ttl=300)
def get_trend(f): return revenue_trend(f)
@st.cache_data(ttl=300)
def get_daily(d): return daily_series(d)
@st.cache_data(ttl=300)
def get_reg(d): e = dt.date.today(); return region_performance(e - dt.timedelta(days=d), e)
@st.cache_data(ttl=300)
def get_cat(d): e = dt.date.today(); return category_performance(e - dt.timedelta(days=d), e)
@st.cache_data(ttl=300)
def get_an(): return detect_all()


anoms = get_an()
high = sum(1 for a in anoms if a["severity"] == "high")
snap0 = get_snap(30)

with st.sidebar:
    st.markdown("#### FinanceOps")
    window = st.selectbox("Look-back window", [7, 30, 60, 90], index=1, format_func=lambda d: f"Last {d} days")
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[
        st.radio("Granularity", ["Daily", "Weekly", "Monthly"], index=0)]
    st.markdown('<div class="eyebrow">Live health</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sb-stat"><span>Open alerts</span><b>{len(anoms)}</b></div>'
                f'<div class="sb-stat"><span>High severity</span><b style="color:{BAD}">{high}</b></div>'
                f'<div class="sb-stat"><span>Data through</span><b>{snap0["period_end"]}</b></div>',
                unsafe_allow_html=True)

snap = get_snap(window)

st.markdown("## FinanceOps")
st.markdown(f'<span style="color:{MUTED};font-size:13px">Executive dashboard · {snap["period_start"]} → {snap["period_end"]}</span>', unsafe_allow_html=True)

ds = get_daily(window)
rev_s = ds["revenue"].tolist() if not ds.empty else []
ord_s = ds["orders"].tolist() if not ds.empty else []
ref_s = ds["refunds"].tolist() if not ds.empty else []

st.markdown('<div class="eyebrow">Headline metrics</div>', unsafe_allow_html=True)
r1 = st.columns(4)
card(r1[0], "Revenue", fmt_money(snap["revenue"]), ACCENT, series=rev_s)
card(r1[1], "Gross Margin", f'{snap["gross_margin_pct"]:.1f}%', GOOD)
card(r1[2], "Orders", f'{snap["orders"]:,}', "#0EA5E9", delta=snap["order_growth_pct"], series=ord_s)
card(r1[3], "Retention", f'{snap["retention_pct"]:.1f}%', GOOD)
st.write("")
r2 = st.columns(4)
card(r2[0], "Unique Customers", f'{snap["unique_customers"]:,}', "#8B5CF6")
card(r2[1], "Return Rate", f'{snap["return_rate_pct"]:.1f}%', BAD)
card(r2[2], "Refund Rate", f'{snap["refund_rate_pct"]:.1f}%', BAD, series=ref_s)
card(r2[3], "Avg Order Value", fmt_money(snap["revenue"]/snap["orders"]) if snap["orders"] else "—", "#F59E0B")

st.markdown('<div class="eyebrow">Revenue trend</div>', unsafe_allow_html=True)
trend = get_trend(freq)
if not trend.empty:
    cutoff = pd.Timestamp(dt.date.today() - dt.timedelta(days=window))
    trend = trend[trend["period"] >= cutoff]
if not trend.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend["period"], y=trend["revenue"], mode="lines",
        line=dict(color=ACCENT, width=2.5), fill="tozeroy", fillcolor="rgba(79,70,229,.07)",
        name="Revenue", hovertemplate="%{x|%d %b}<br>Rs %{y:,.0f}<extra></extra>"))
    if len(trend) >= 7:
        ma = trend["revenue"].rolling(7).mean()
        fig.add_trace(go.Scatter(x=trend["period"], y=ma, mode="lines",
            line=dict(color="#94A3B8", width=1.5, dash="dash"), name="7-pt avg",
            hovertemplate="avg %{y:,.0f}<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=6, b=0), plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, color=MUTED),
        yaxis=dict(gridcolor=GRID, color=MUTED, zeroline=False),
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)

cL, cR = st.columns(2)
with cL:
    st.markdown('<div class="eyebrow">Revenue by region</div>', unsafe_allow_html=True)
    reg = get_reg(window)
    if not reg.empty:
        fig = go.Figure(go.Bar(x=reg["revenue"], y=reg["zone"], orientation="h",
            marker_color=CAT_COLORS[:len(reg)], hovertemplate="%{y}: Rs %{x:,.0f}<extra></extra>"))
        fig.update_layout(height=260, margin=dict(l=0, r=0, t=6, b=0), plot_bgcolor="white",
            paper_bgcolor="rgba(0,0,0,0)", xaxis=dict(gridcolor=GRID, color=MUTED), yaxis=dict(color=INK))
        st.plotly_chart(fig, use_container_width=True)
with cR:
    st.markdown('<div class="eyebrow">Revenue by category</div>', unsafe_allow_html=True)
    cat = get_cat(window)
    if not cat.empty:
        fig = go.Figure(go.Pie(labels=cat["category"], values=cat["revenue"], hole=.6,
            marker=dict(colors=CAT_COLORS), hovertemplate="%{label}: Rs %{value:,.0f} (%{percent})<extra></extra>"))
        fig.update_layout(height=260, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-.12), font=dict(color=INK))
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<div class="eyebrow">Anomaly alerts</div>', unsafe_allow_html=True)
if not anoms:
    st.success("No anomalies detected.")
else:
    sev = {"high": ("#FEE2E2", "#991B1B", BAD), "medium": ("#FFEDD5", "#9A3412", "#EA580C"), "low": ("#FEF9C3", "#854D0E", "#CA8A04")}
    for a in anoms[:10]:
        bg, fg, edge = sev[a["severity"]]
        st.markdown(f'<div class="alert" style="--c:{edge}">'
            f'<div><span class="pill" style="background:{bg};color:{fg}">{a["severity"].upper()}</span>'
            f'<b>{a["date"]}</b> · {a["message"]}</div>'
            f'<div style="color:{edge};font-weight:800">{a["deviation_pct"]:+.0f}%</div></div>',
            unsafe_allow_html=True)