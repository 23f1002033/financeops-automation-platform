"""KPI engine — single source of truth for all finance metrics."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

from financeops.db.session import engine
from financeops.logging_config import get_logger

logger = get_logger(__name__)


_ORDERS_SQL = """
SELECT
    f.order_id,
    d.full_date            AS order_date,
    d.year, d.month, d.month_name, d.week, d.quarter, d.is_weekend,
    c.customer_id, c.segment,
    p.category, p.subcategory,
    r.zone, r.state, r.city, r.region_id,
    f.quantity, f.gross_revenue, f.discount, f.cost, f.net_revenue
FROM fact_orders f
JOIN dim_date d     ON f.date_key = d.date_key
JOIN dim_customer c ON f.customer_key = c.customer_key
JOIN dim_product p  ON f.product_key = p.product_key
JOIN dim_region r   ON f.region_key = r.region_key
"""

_RETURNS_SQL = """
SELECT f.order_id, d.full_date AS return_date, r.zone, f.refund_amount, f.reason
FROM fact_returns f
JOIN dim_date d   ON f.date_key = d.date_key
JOIN dim_region r ON f.region_key = r.region_key
"""


def load_orders() -> pd.DataFrame:
    df = pd.read_sql(text(_ORDERS_SQL), engine)
    if not df.empty:
        df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def load_returns() -> pd.DataFrame:
    df = pd.read_sql(text(_RETURNS_SQL), engine)
    if not df.empty:
        df["return_date"] = pd.to_datetime(df["return_date"])
    return df


@dataclass
class KpiSnapshot:
    period_start: str
    period_end: str
    revenue: float
    gross_margin_pct: float
    orders: int
    unique_customers: int
    return_rate_pct: float
    refund_rate_pct: float
    retention_pct: float
    order_growth_pct: float

    def to_dict(self) -> dict:
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


def _filter_period(df: pd.DataFrame, date_col: str, start: dt.date | None, end: dt.date | None) -> pd.DataFrame:
    if df.empty:
        return df
    out = df
    if start is not None:
        out = out[out[date_col] >= pd.Timestamp(start)]
    if end is not None:
        out = out[out[date_col] <= pd.Timestamp(end)]
    return out


def compute_snapshot(start: dt.date | None = None, end: dt.date | None = None) -> KpiSnapshot:
    orders = load_orders()
    returns = load_returns()

    cur = _filter_period(orders, "order_date", start, end)
    if cur.empty:
        return KpiSnapshot(str(start), str(end), 0, 0, 0, 0, 0, 0, 0, 0)

    revenue = float(cur["net_revenue"].sum())
    cogs = float(cur["cost"].sum())
    gross_margin_pct = ((revenue - cogs) / revenue * 100) if revenue else 0.0
    n_orders = int(cur["order_id"].nunique())
    unique_customers = int(cur["customer_id"].nunique())

    cur_returns = _filter_period(returns, "return_date", start, end)
    returned_orders = int(cur_returns["order_id"].nunique()) if not cur_returns.empty else 0
    refund_amount = float(cur_returns["refund_amount"].sum()) if not cur_returns.empty else 0.0
    return_rate = (returned_orders / n_orders * 100) if n_orders else 0.0
    refund_rate = (refund_amount / revenue * 100) if revenue else 0.0

    if start is not None:
        prior = orders[orders["order_date"] < pd.Timestamp(start)]
        prior_customers = set(prior["customer_id"].unique())
        cur_customers = set(cur["customer_id"].unique())
        retained = len(cur_customers & prior_customers)
        retention = (retained / len(cur_customers) * 100) if cur_customers else 0.0

        span = (end - start).days + 1 if end else 30
        prev_start = start - dt.timedelta(days=span)
        prev_end = start - dt.timedelta(days=1)
        prev = _filter_period(orders, "order_date", prev_start, prev_end)
        prev_orders = int(prev["order_id"].nunique())
        order_growth = ((n_orders - prev_orders) / prev_orders * 100) if prev_orders else 0.0
    else:
        retention = 0.0
        order_growth = 0.0

    return KpiSnapshot(
        period_start=str(cur["order_date"].min().date()),
        period_end=str(cur["order_date"].max().date()),
        revenue=revenue, gross_margin_pct=gross_margin_pct,
        orders=n_orders, unique_customers=unique_customers,
        return_rate_pct=return_rate, refund_rate_pct=refund_rate,
        retention_pct=retention, order_growth_pct=order_growth,
    )


def revenue_trend(freq: str = "D") -> pd.DataFrame:
    """Revenue/orders/margin time series. freq in {'D','W','M'}."""
    freq = {"D": "D", "W": "W", "M": "ME"}.get(freq, freq)
    orders = load_orders()
    if orders.empty:
        return pd.DataFrame(columns=["period", "revenue", "orders", "gross_margin_pct"])

    g = (
        orders.set_index("order_date")
        .groupby(pd.Grouper(freq=freq))
        .agg(
            revenue=("net_revenue", "sum"),
            cost=("cost", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
        .rename(columns={"order_date": "period"})
    )
    g["gross_margin_pct"] = ((g["revenue"] - g["cost"]) / g["revenue"].replace(0, pd.NA) * 100).round(2)
    g["revenue"] = g["revenue"].round(2)
    return g.drop(columns="cost")


def region_performance(start: dt.date | None = None, end: dt.date | None = None) -> pd.DataFrame:
    orders = _filter_period(load_orders(), "order_date", start, end)
    if orders.empty:
        return pd.DataFrame(columns=["zone", "revenue", "orders", "gross_margin_pct"])
    g = (
        orders.groupby("zone")
        .agg(revenue=("net_revenue", "sum"), cost=("cost", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    g["gross_margin_pct"] = ((g["revenue"] - g["cost"]) / g["revenue"] * 100).round(2)
    g["revenue"] = g["revenue"].round(2)
    return g.drop(columns="cost").sort_values("revenue", ascending=False)


def category_performance(start: dt.date | None = None, end: dt.date | None = None) -> pd.DataFrame:
    orders = _filter_period(load_orders(), "order_date", start, end)
    if orders.empty:
        return pd.DataFrame(columns=["category", "revenue", "orders"])
    g = (
        orders.groupby("category")
        .agg(revenue=("net_revenue", "sum"), orders=("order_id", "nunique"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    g["revenue"] = g["revenue"].round(2)
    return g


def daily_series(days: int = 30) -> pd.DataFrame:
    """Compact daily series for sparklines: revenue, orders, refunds per day."""
    orders = load_orders()
    returns = load_returns()
    if orders.empty:
        return pd.DataFrame(columns=["date", "revenue", "orders", "refunds"])

    end = orders["order_date"].max()
    start = end - pd.Timedelta(days=days)
    o = orders[orders["order_date"] >= start]

    g = (o.set_index("order_date").groupby(pd.Grouper(freq="D"))
         .agg(revenue=("net_revenue", "sum"), orders=("order_id", "nunique"))
         .reset_index().rename(columns={"order_date": "date"}))

    if not returns.empty:
        r = returns[returns["return_date"] >= start]
        rr = (r.set_index("return_date").groupby(pd.Grouper(freq="D"))["refund_amount"]
              .sum().reset_index().rename(columns={"return_date": "date", "refund_amount": "refunds"}))
        g = g.merge(rr, on="date", how="left")
    if "refunds" not in g.columns:
        g["refunds"] = 0
    g = g.fillna(0)
    return g