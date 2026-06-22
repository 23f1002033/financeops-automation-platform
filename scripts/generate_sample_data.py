"""Generate realistic synthetic finance datasets (orders + returns)."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ZONES = {
    "North": ["Delhi", "Gurugram", "Jaipur"],
    "South": ["Bengaluru", "Chennai", "Hyderabad"],
    "East": ["Kolkata", "Patna", "Guwahati"],
    "West": ["Mumbai", "Pune", "Ahmedabad"],
}
CATEGORIES = {
    "Electronics": ["Mobiles", "Laptops", "Audio"],
    "Apparel": ["Men", "Women", "Kids"],
    "Home": ["Kitchen", "Decor", "Furniture"],
    "Grocery": ["Staples", "Beverages", "Snacks"],
}
SEGMENTS = ["Retail", "SMB", "Enterprise"]
REASONS = ["Damaged", "Wrong item", "Late delivery", "Changed mind", "Defective"]


def generate(days: int, out_dir: Path, seed: int = 7) -> tuple[Path, Path]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    start = dt.date.today() - dt.timedelta(days=days - 1)
    dates = [start + dt.timedelta(days=i) for i in range(days)]

    order_rows = []
    return_rows = []
    order_counter = 1000

    for i, d in enumerate(dates):
        weekly = 1.0 + 0.15 * np.sin(2 * np.pi * d.weekday() / 7)
        growth = 1.0 + 0.0015 * i
        base = int(rng.normal(60, 8) * weekly * growth)

        # Anomaly 1: revenue cliff for 2 days around 60% mark
        cliff = 0.45 if (days * 0.60) <= i < (days * 0.60 + 2) else 1.0
        n_orders = max(5, int(base * cliff))

        for _ in range(n_orders):
            zone = rng.choice(list(ZONES))
            city = rng.choice(ZONES[zone])
            cat = rng.choice(list(CATEGORIES))
            sub = rng.choice(CATEGORIES[cat])
            seg = rng.choice(SEGMENTS, p=[0.7, 0.2, 0.1])
            qty = int(rng.integers(1, 5))
            unit_price = max(120, float(rng.normal(1500, 600)))
            gross = round(unit_price * qty, 2)
            discount = round(gross * rng.uniform(0, 0.18), 2)
            cost = round(gross * rng.uniform(0.55, 0.78), 2)
            cust_id = f"CUST{int(rng.integers(1, 1200)):05d}"
            order_id = f"ORD{order_counter:07d}"
            order_counter += 1
            order_rows.append(dict(
                order_id=order_id, order_date=d, customer_id=cust_id,
                product_id=f"PRD{cat[:2].upper()}{int(rng.integers(1, 400)):04d}",
                region_id=f"{zone[:1]}{city[:3].upper()}",
                category=cat, subcategory=sub, segment=seg,
                zone=zone, state=zone, city=city,
                quantity=qty, gross_revenue=gross, discount=discount, cost=cost,
            ))

            # ~6% orders get returned later
            if rng.random() < 0.06:
                rdate = d + dt.timedelta(days=int(rng.integers(1, 6)))
                if rdate <= dates[-1]:
                    refund = round((gross - discount) * rng.uniform(0.6, 1.0), 2)
                    return_rows.append(dict(
                        order_id=order_id, return_date=rdate,
                        region_id=f"{zone[:1]}{city[:3].upper()}",
                        refund_amount=refund, reason=rng.choice(REASONS)))

        # Anomaly 2: refund spike near 80% mark
        if int(days * 0.80) <= i < int(days * 0.80) + 1:
            for _ in range(40):
                zone = rng.choice(list(ZONES))
                city = rng.choice(ZONES[zone])
                return_rows.append(dict(
                    order_id=f"ORD{int(rng.integers(1000, order_counter)):07d}",
                    return_date=d, region_id=f"{zone[:1]}{city[:3].upper()}",
                    refund_amount=round(float(rng.normal(2200, 500)), 2),
                    reason="Defective"))

    orders = pd.DataFrame(order_rows)
    returns = pd.DataFrame(return_rows)

    # Inject dirty rows so validation has work to do
    if len(orders) > 20:
        orders.loc[orders.index[5], "gross_revenue"] = -10      # negative
        orders.loc[orders.index[9], "customer_id"] = None        # missing key
        orders.loc[orders.index[14], "quantity"] = 0             # below min

    orders_path = out_dir / "orders.csv"
    returns_path = out_dir / "returns.csv"
    orders.to_csv(orders_path, index=False)
    returns.to_csv(returns_path, index=False)
    print(f"Wrote {len(orders):,} orders -> {orders_path}")
    print(f"Wrote {len(returns):,} returns -> {returns_path}")
    return orders_path, returns_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--out", type=str, default="data/raw")
    args = parser.parse_args()
    generate(args.days, Path(args.out))