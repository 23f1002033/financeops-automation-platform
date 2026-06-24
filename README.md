# 💰 FinanceOps Automation Platform

**A finance analyst's worst Monday: 200 rows of yesterday's orders, a blank report template, and a CFO who wants numbers by 9 AM.**

This platform deletes that Monday. It ingests the raw data, models it properly, computes every KPI, hunts down anomalies, and drops a polished executive PDF on the table — before anyone's had their first coffee.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/api-FastAPI-009688)
![PostgreSQL](https://img.shields.io/badge/db-PostgreSQL-336791)
![Tests](https://img.shields.io/badge/tests-14%20passing-success)
![Docker](https://img.shields.io/badge/deploy-Docker%20Compose-2496ED)

---

## Why this exists

Operations-heavy companies (think Delhivery, Swiggy, Amazon) drown their finance teams in daily CSVs. Someone spends three hours every morning copy-pasting numbers into the same report. That person could be doing actual analysis.

**FinanceOps turns those three hours into one command.**

---

## What it actually does

| Stage | What happens |
|---|---|
| 📥 **Ingest** | Reads CSV/Excel, validates every row, quarantines bad data, and refuses to load the same file twice (no double-counted revenue). |
| 🗄️ **Model** | Lands everything in a Kimball **star schema** — built for fast finance roll-ups. |
| 📊 **Measure** | Revenue, gross margin, return & refund rates, retention, order growth, region/category splits, daily→monthly trends. |
| 🚨 **Detect** | Flags revenue drops, refund spikes & order declines using rolling z-scores — each alert in plain English, not jargon. |
| 📄 **Report** | Executive summary, CSV exports, and a branded PDF. Automatically. |
| 🤖 **Automate** | One scheduled pipeline runs the whole chain every morning. |

The catch? **The API, the dashboard, and the PDF all read from the same engine** — so they can never disagree on a number. One source of truth, no exceptions.

---

## See it in 60 seconds

```bash
pip install -r requirements.txt
export PYTHONPATH=src

python scripts/generate_sample_data.py --days 120   # fake-but-realistic data
python scripts/seed_database.py                      # build + load the warehouse
python scripts/run_daily_pipeline.py                 # KPIs + anomalies + PDF/CSV

uvicorn financeops.api.main:app --reload --port 8000 # 👉 http://localhost:8000/docs
streamlit run dashboard/app.py                       # 👉 http://localhost:8501
```

Want the real deal with PostgreSQL? One line:

```bash
docker compose up --build      # Postgres + API + dashboard + scheduler, all wired up
```

---

## Under the hood

```
CSV / Excel
  |
  v
Ingestion        ->  validate, quality-check, idempotent audit
  |
  v
Star Schema      ->  PostgreSQL: 4 dimensions + 2 facts
  |
  v
Shared engine    ->  KPIs, Anomalies, Reporting
  |
  |--> FastAPI      (REST + Swagger)
  |--> Streamlit    (live dashboard + alerts)

The daily scheduler runs this whole chain every morning at 6 AM.
```
---

## Things I'm quietly proud of

- **Idempotency** — found this bug myself by re-running the pipeline and watching revenue double. Now every file is SHA-256 fingerprinted; loading it twice is a no-op.
- **Explainable anomalies** — tuned a noisy 82-alert feed down to ~36 *material* ones, each with a one-line "why".
- **Logs to stderr, data to stdout** — so the pipeline's JSON output stays pipeable. Small thing, real-world thinking.
- **14 tests, isolated DB** — the suite spins up its own throwaway database; it never touches your real data.

---

## Tech stack

`Python` · `PostgreSQL` · `pandas` · `SQLAlchemy` · `FastAPI` · `Streamlit` · `Plotly` · `ReportLab` · `APScheduler` · `Docker`

## Layout

```
src/financeops/   ingestion · db · kpi · anomaly · reporting · api · automation
dashboard/        Streamlit app
sql/              warehouse DDL + advanced KPI queries (CTEs, window functions)
scripts/          data generator · seeding · daily pipeline
tests/            pytest suite with a seeded-DB fixture
```

## Tests

```bash
PYTHONPATH=src pytest        # 14 passing - ingestion, KPI, anomaly, API
```

---

## License

MIT — take it, learn from it, build on it.