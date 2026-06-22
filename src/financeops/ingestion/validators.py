"""Declarative validation rules for incoming raw datasets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd


@dataclass
class ColumnRule:
    name: str
    dtype: str                       # "str" | "int" | "float" | "date"
    required: bool = True
    min_value: float | None = None
    allowed: set[str] | None = None


@dataclass
class DatasetSchema:
    name: str
    columns: list[ColumnRule]
    row_checks: list[Callable[[pd.Series], str | None]] = field(default_factory=list)

    @property
    def required_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.required]


def _positive_revenue(row: pd.Series) -> str | None:
    if row.get("gross_revenue", 0) < 0:
        return "negative gross_revenue"
    return None


def _cost_not_exceed_gross(row: pd.Series) -> str | None:
    if row.get("cost", 0) > row.get("gross_revenue", 0) * 1.5:
        return "cost implausibly high vs gross_revenue"
    return None


ORDERS_SCHEMA = DatasetSchema(
    name="orders",
    columns=[
        ColumnRule("order_id", "str"),
        ColumnRule("order_date", "date"),
        ColumnRule("customer_id", "str"),
        ColumnRule("product_id", "str"),
        ColumnRule("region_id", "str"),
        ColumnRule("category", "str", required=False),
        ColumnRule("subcategory", "str", required=False),
        ColumnRule("segment", "str", required=False),
        ColumnRule("zone", "str", required=False),
        ColumnRule("state", "str", required=False),
        ColumnRule("city", "str", required=False),
        ColumnRule("quantity", "int", min_value=1),
        ColumnRule("gross_revenue", "float", min_value=0),
        ColumnRule("discount", "float", required=False, min_value=0),
        ColumnRule("cost", "float", min_value=0),
    ],
    row_checks=[_positive_revenue, _cost_not_exceed_gross],
)

RETURNS_SCHEMA = DatasetSchema(
    name="returns",
    columns=[
        ColumnRule("order_id", "str"),
        ColumnRule("return_date", "date"),
        ColumnRule("region_id", "str"),
        ColumnRule("refund_amount", "float", min_value=0),
        ColumnRule("reason", "str", required=False),
    ],
)

SCHEMAS: dict[str, DatasetSchema] = {
    "orders": ORDERS_SCHEMA,
    "returns": RETURNS_SCHEMA,
}


_DTYPE_COERCE = {
    "str": lambda s: s.astype("string"),
    "int": lambda s: pd.to_numeric(s, errors="coerce").astype("Int64"),
    "float": lambda s: pd.to_numeric(s, errors="coerce"),
    "date": lambda s: pd.to_datetime(s, errors="coerce"),
}


def validate(df: pd.DataFrame, schema: DatasetSchema) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate ``df`` against ``schema``. Returns (clean_df, rejected_df)."""
    missing = [c for c in schema.required_columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset '{schema.name}' is missing required columns: {missing}"
        )

    df = df.copy()
    reasons = pd.Series("", index=df.index)

    # 1. dtype coercion
    for col in schema.columns:
        if col.name not in df.columns:
            df[col.name] = pd.NA
        df[col.name] = _DTYPE_COERCE[col.dtype](df[col.name])

    # 2. column-level constraints
    for col in schema.columns:
        series = df[col.name]
        if col.required:
            null_mask = series.isna()
            reasons[null_mask & (reasons == "")] = f"missing {col.name}"
        if col.min_value is not None:
            bad = (series < col.min_value).fillna(False)
            reasons[bad & (reasons == "")] = f"{col.name} < {col.min_value}"
        if col.allowed is not None:
            bad = ~series.isin(col.allowed) & series.notna()
            reasons[bad & (reasons == "")] = f"{col.name} not in allowed set"

    # 3. row-level business checks
    for check in schema.row_checks:
        for idx, row in df[reasons == ""].iterrows():
            msg = check(row)
            if msg:
                reasons[idx] = msg

    rejected_mask = reasons != ""
    rejected = df[rejected_mask].copy()
    rejected["_reject_reason"] = reasons[rejected_mask]
    clean = df[~rejected_mask].copy()
    return clean, rejected