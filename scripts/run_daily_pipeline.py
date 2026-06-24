"""Run the daily finance pipeline once (manual trigger / cron target)."""
from __future__ import annotations

import json

from financeops.automation.scheduler import run_daily_pipeline


def main() -> None:
    report = run_daily_pipeline()
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()