from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings, populated from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    app_name: str = "FinanceOps Automation Platform"
    environment: str = "development"          # development | staging | production
    log_level: str = "INFO"

    # Database 
    # Production mein yeh PostgreSQL hota hai, e.g.
    # postgresql+psycopg2://user:pass@host:5432/financeops
    # Local demo ke liye SQLite pe fall back ho jaata hai, taaki bina kisi
    # external service ke pura pipeline chal jaaye.
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'financeops.db'}"
    db_echo: bool = False

    # Paths 
    raw_data_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_data_dir: Path = PROJECT_ROOT / "data" / "processed"
    reports_dir: Path = PROJECT_ROOT / "data" / "reports"

    #Anomaly detection
    anomaly_zscore_threshold: float = 2.5     # rolling z-score trigger
    anomaly_pct_drop_threshold: float = 0.20  # 20% day-over-day drop
    anomaly_rolling_window: int = 7           # days

    def ensure_dirs(self) -> None:
        for p in (self.raw_data_dir, self.processed_data_dir, self.reports_dir):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the settings object."""
    settings = Settings()
    settings.ensure_dirs()
    return settings