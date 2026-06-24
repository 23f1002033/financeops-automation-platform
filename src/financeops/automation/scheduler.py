"""Automation layer - the orchestrated daily workflow + scheduler."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from financeops.anomaly.detector import detect_all
from financeops.config import get_settings
from financeops.db.session import init_db
from financeops.ingestion.loaders import ingest_file
from financeops.kpi.engine import compute_snapshot
from financeops.logging_config import get_logger
from financeops.reporting.csv_export import export_csv_bundle
from financeops.reporting.pdf_report import generate_pdf_report

logger = get_logger(__name__)
settings = get_settings()

_DATASET_HINTS = {"orders": "orders", "returns": "returns", "refund": "returns"}


def _infer_dataset(filename: str) -> str | None:
    low = filename.lower()
    for hint, ds in _DATASET_HINTS.items():
        if hint in low:
            return ds
    return None


def run_daily_pipeline(inbox: Path | None = None) -> dict:
    """End-to-end daily workflow. Returns a run report."""
    start = dt.datetime.now()
    init_db()
    inbox = inbox or settings.raw_data_dir

    ingested = []
    for f in sorted(Path(inbox).glob("*")):
        if f.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
            continue
        ds = _infer_dataset(f.name)
        if not ds:
            logger.warning("Skipping %s - cannot infer dataset", f.name)
            continue
        try:
            ingested.append(ingest_file(f, ds))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to ingest %s", f.name)
            ingested.append({"source_file": f.name, "status": "failed", "error": str(exc)})

    snapshot = compute_snapshot(
        start=dt.date.today() - dt.timedelta(days=30), end=dt.date.today()
    ).to_dict()
    anomalies = detect_all()
    pdf = generate_pdf_report()
    csvs = export_csv_bundle()

    report = {
        "run_at": start.isoformat(timespec="seconds"),
        "duration_sec": round((dt.datetime.now() - start).total_seconds(), 2),
        "files_ingested": ingested,
        "kpi_snapshot": snapshot,
        "anomaly_count": len(anomalies),
        "pdf_report": str(pdf),
        "csv_reports": csvs,
    }
    logger.info("Daily pipeline finished in %ss", report["duration_sec"])
    return report


def start_scheduler(hour: int = 6, minute: int = 0) -> None:
    """Run the daily pipeline every day at the given time (in-process)."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(run_daily_pipeline, "cron", hour=hour, minute=minute, id="daily_finance_pipeline")
    logger.info("Scheduler started - daily pipeline at %02d:%02d IST", hour, minute)
    scheduler.start()