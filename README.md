# Kathiyawadi Restaurant Market Pricing — Ahmedabad

## Project Overview

This project tracks the vegetarian Kathiyawadi restaurant market in Ahmedabad and produces refreshed pricing benchmarks for analysis in Power BI and a live GitHub Pages view.

## Business Objective

Build and maintain a reliable benchmark dataset for pricing decisions by continuously collecting and curating competitor restaurant and dish-level price signals.

## Live Data Pipeline

### Live-source scope and coverage

- Geography: Ahmedabad, Gujarat, India
- Segment: vegetarian / Kathiyawadi restaurants
- Required fields:
  - Restaurant: name, area, city, type, cuisine, rating, review count, source URL
  - Menu: dish name, price, portion/serving, menu type, timestamp, source URL
  - Pipeline metadata: source system, source record ID, fetch time, match confidence, price validation status
- Refresh frequency: every 12 hours (GitHub Actions cron)

### Sources

- **OpenStreetMap Overpass API** (default live source)
- **Google Places Text Search API** (optional via `GOOGLE_PLACES_API_KEY`)
- **External connector CSV** (`data/external/menu_prices.csv`) for permitted Swiggy/Zomato/public-directory exports

> Notes: source usage must follow each platform’s terms, robots/rate limits, and permitted API access.

### Community experience updates

The live page includes **Share a field experience**. A visitor can submit a recent restaurant experience, optional dish price, and a public source link through a GitHub Issue form. GitHub Actions validates the fields, stores the submission in `data/external/experience_submissions.csv`, and refreshes the curated tables and page.

To enable the public map connector, add `GOOGLE_PLACES_API_KEY` as a repository secret. OpenStreetMap discovery runs without a key. Google Places provides restaurant discovery and ratings; menu prices must come from `data/external/menu_prices.csv`, a permitted connector export, or a submitted field observation. The pipeline does not scrape restricted delivery platforms.

### Repeatable ingestion layer

Pipeline script: `/home/runner/work/data_restarant/data_restarant/scripts/live_pipeline.py`

It performs:
1. Source fetch (with per-source success/failed/skipped state)
2. Raw snapshot write to `data/raw/<timestamp>/`
3. Normalization into Restaurant/Product/Fact_Menu_Price shape
4. Cross-source dedup + entity matching
5. Data quality filtering and standardization
6. Curated latest + historical output write
7. Monitoring metrics and error logs

### Deduplication and entity matching

- Stable keys: `Source_Record_ID` when available
- Fuzzy match fallback: weighted restaurant-name + area similarity
- Merge behavior: combine attributes into one canonical restaurant record
- Confidence: `Match_Confidence` stored per canonical record

### Data quality rules

- Price parsing and numeric validation
- Invalid/out-of-range filtering
- IQR-based outlier tagging
- Dish-name normalization (canonical naming)
- `Price_Validation_Status` and confidence fields retained for audit

### Incremental refresh storage

- Raw snapshots: `data/raw/<timestamp>/...`
- Curated latest: `data/curated/latest/`
- Curated history: `data/curated/history/<timestamp>/`

This supports traceability and rollback while keeping a stable “latest” layer for dashboards.

### Monitoring and failure handling

- Source status log: `data/monitoring/source_status.csv`
- Refresh metrics: `data/monitoring/refresh_metrics.csv`
- Error log: `data/monitoring/error_log.jsonl`
- Fallback behavior:
  - If a live source fails, pipeline continues with available sources
  - If menu rows are unavailable, historical benchmark medians are used as fallback seed data

## Power BI and Live Page

### Power BI model usage

Use these curated files as the model input:
- `data/curated/latest/Restaurant.csv`
- `data/curated/latest/Product.csv`
- `data/curated/latest/Fact_Menu_Price.csv`

Set Power BI scheduled refresh against the curated latest layer so KPI visuals (avg/median/min/max and competitor comparisons) update automatically.

### Live GitHub page

- Generated page: `docs/index.html`
- Build script: `/home/runner/work/data_restarant/data_restarant/scripts/build_pages.py`
- Auto-refreshed by GitHub Actions workflow:
  - `.github/workflows/live-data-pipeline.yml`

Default domain:
- `https://trambak001.github.io/data_restarant/`

Optional custom domain:
- Set repository variable `PAGES_CUSTOM_DOMAIN`
- Workflow writes `docs/CNAME` automatically
- Point DNS to GitHub Pages records and enable Pages in repo settings

## Compliance and limitations

- Respect API terms, scraping restrictions, and rate limits for all providers.
- Google Places requires a valid API key and billing-enabled project.
- Platform menu APIs may be restricted; external connector CSV is provided for compliant imports.
- Missing ratings/reviews/menu details are preserved as null where unavailable.

## Tools Used

- Python (pandas, requests)
- GitHub Actions
- Power BI
- Excel

## Repository Files

| File | Description |
|---|---|
| `scripts/live_pipeline.py` | Live ingestion, normalization, matching, quality, and curated output builder |
| `scripts/build_pages.py` | Builds the live GitHub Pages dashboard page from curated latest data |
| `.github/workflows/live-data-pipeline.yml` | Scheduled refresh workflow (12-hour cron + manual dispatch) |
| `data/raw/` | Raw source snapshots per run |
| `data/curated/latest/` | Latest cleaned tables used by Power BI/live page |
| `data/curated/history/` | Versioned curated outputs by timestamp |
| `data/monitoring/` | Source status, refresh metrics, and error logs |
| `docs/index.html` | Published live market page |
| `LICENSE` | MIT license |
