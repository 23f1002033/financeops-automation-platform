# FinanceOps Automation Platform

> Production-style internal tool that automates a corporate finance team's daily
> reporting: ingest operational data - model it in a star schema - compute KPIs -
> detect anomalies - ship an executive PDF, automatically, every morning.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/api-FastAPI-009688)
![PostgreSQL](https://img.shields.io/badge/db-PostgreSQL-336791)
![Tests](https://img.shields.io/badge/tests-14%20passing-success)
![Docker](https://img.shields.io/badge/deploy-Docker%20Compose-2496ED)

## The problem
Finance teams at operations-heavy companies receive daily datasets (orders,
returns, refunds) and spend hours manually building reports, tracking KPIs,
spotting anomalies, and emailing stakeholders. This platform automates that loop.

## What it does
- **Ingests** CSV/Excel with schema validation, data-quality checks, error
  reporting, and **idempotent** loads (no double-counting revenue).
- **Models** data in a Kimball **star schema** (PostgreSQL / SQLite).
- **Computes KPIs**: revenue, gross margin, return/refund rate, retention,
  order growth, region & category performance, daily/weekly/monthly trends.
- **Detects anomalies**: revenue drops, refund spikes, order declines, with
  severity and a plain-English explanation for each alert.
- **Reports**: executive summary, CSV exports, and a branded **PDF**.
- **Serves**: a **FastAPI** REST API (Swagger docs) and a **Streamlit** dashboard.
- **Automates**: a scheduled daily pipeline that runs the whole thing.

## Architecture
\`\`\`
CSV/Excel - Ingestion (validate, QC, audit)- Star Schema
    ->KPI + Anomaly + Reporting engines (shared core) -> FastAPI + Streamlit
                          Daily scheduler
\`\`\`

## Quickstart (zero external services)
\`\`\`bash
pip install -r requirements.txt
export PYTHONPATH=src

python scripts/generate_sample_data.py --days 120   # synthetic orders + returns
python scripts/seed_database.py                      # init schema + load (SQLite)
python scripts/run_daily_pipeline.py                 # KPIs + anomalies + PDF/CSV

uvicorn financeops.api.main:app --reload --port 8000 # API  -> http://localhost:8000/docs
streamlit run dashboard/app.py                       # dash -> http://localhost:8501
\`\`\`

## Full stack with Docker (PostgreSQL)
\`\`\`bash
docker compose up --build
# api:8000  dashboard:8501  postgres:5432  + daily scheduler
\`\`\`

## Tests
\`\`\`bash
PYTHONPATH=src pytest        # 14 tests: ingestion, KPI, anomaly, API
\`\`\`

## Project layout
\`\`\`
src/financeops/   ingestion · db · kpi · anomaly · reporting · api · automation
dashboard/        Streamlit app
sql/              warehouse DDL + advanced KPI queries
scripts/          data generator · seeding · daily pipeline
tests/            pytest suite with seeded-DB fixture
\`\`\`

## Tech stack
Python · PostgreSQL · pandas · SQLAlchemy · FastAPI · Streamlit · Plotly ·
ReportLab · APScheduler · Docker.

## License
MIT
