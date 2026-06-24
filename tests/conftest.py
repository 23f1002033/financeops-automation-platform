"""Pytest fixtures — isolated temp DB seeded with generated data."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Point the app at an isolated DB before importing any financeops module,
# because the engine is created at import time.
_TMP = Path(tempfile.mkdtemp(prefix="financeops_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["ENVIRONMENT"] = "development"


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    from scripts.generate_sample_data import generate
    from financeops.db.session import init_db
    from financeops.ingestion.loaders import ingest_file

    raw = _TMP / "raw"
    orders_path, returns_path = generate(days=60, out_dir=raw, seed=42)
    init_db()
    ingest_file(orders_path, "orders")
    ingest_file(returns_path, "returns")
    yield