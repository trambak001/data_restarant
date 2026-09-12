# Kathiyawadi Restaurant Market Pricing — Ahmedabad

[![Live Data Pipeline](https://github.com/trambak001/data_restaurant/actions/workflows/live-data-pipeline.yml/badge.svg)](https://github.com/trambak001/data_restaurant/actions/workflows/live-data-pipeline.yml)

> **Live benchmark pricing data** for Kathiyawadi / Gujarati vegetarian restaurants in Ahmedabad, updated every 12 hours via automated pipeline.

---

## Overview

The **Kathiyawadi Market Intelligence** platform ingests restaurant and menu data from multiple open sources, normalises and deduplicates it across sources, and publishes three curated dimension tables — `Restaurant`, `Product`, and `Fact_Menu_Price` — to GitHub Pages and Power BI dashboards.

### Business Objective

Build and maintain a reliable benchmark dataset for pricing decisions by continuously collecting and curating competitor restaurant and dish-level price signals across Ahmedabad.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Source Layer (live_pipeline.py)          │
│                                                          │
│  OpenStreetMap  Google Places  Seed CSVs  Community      │
│  Overpass API   (optional key) (External)  Issues        │
└──────┬───────────┬──────────────┬──────────┬────────────-┘
       │           │              │          │
       ▼           ▼              ▼          ▼
┌──────────────────────────────────────────────────────────┐
│             Ingestion & Normalisation                    │
│  normalize_area · normalize_cuisine · dedup_restaurants  │
│  build_products (fuzzy dedup) · quality_filter_prices    │
└──────────────────────────┬───────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
┌──────────────────┐              ┌──────────────────────┐
│ data/curated/    │              │ data/monitoring/     │
│   latest/        │              │  source_status.csv   │
│   Restaurant.csv │              │  refresh_metrics.csv │
│   Product.csv    │              │  error_log.jsonl     │
│   Fact_Menu_Price│              └──────────────────────┘
└──────┬───────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│              Presentation Layer (build_pages.py)          │
│   docs/index.html (GitHub Pages)  ·  Power BI (CSV feed) │
└──────────────────────────────────────────────────────────┘
```

---

## SLA & Refresh Schedule

| Trigger | Schedule | Sources | Fallback |
|---|---|---|---|
| Scheduled cron | Every 12 hours | OSM Overpass + optional Google Places + Community | Historical median prices |
| Community submission | On GitHub Issue opened (label: `market-experience`) | Community experience form | — |
| Manual dispatch | On-demand via GitHub Actions UI | All sources | — |

**Failure behaviour**: if any live source fails, the pipeline continues with available sources and logs the error to `data/monitoring/error_log.jsonl`. If all menu sources fail, historical benchmark medians from `data/external/seed_fact_menu_price.csv` are used as seed prices.

---

## Live Data Pipeline

### Source coverage

- **Geography**: Ahmedabad (and Gandhinagar), Gujarat, India
- **Segment**: vegetarian / Kathiyawadi restaurants
- **Required fields**:
  - Restaurant: name, area, city, type, cuisine, rating, review count, source URL
  - Menu: dish name, price, portion/serving, menu type, timestamp, source URL
  - Pipeline metadata: source system, source record ID, fetch time, match confidence, price validation status
- **Refresh frequency**: every 12 hours (GitHub Actions cron)

### Sources

| Source | Key required | Notes |
|---|---|---|
| OpenStreetMap Overpass API | None | Tries 3 mirror endpoints with exponential backoff |
| Google Places Text Search API | `GOOGLE_PLACES_API_KEY` secret | Optional; skipped gracefully if absent |
| External connector CSV | None | `data/external/menu_prices.csv` for compliant imports |
| Community experience (GitHub Issues) | None | Validated and stored to `data/external/experience_submissions.csv` |
| Seed workbook CSVs | None | `data/external/seed_*.csv` — stable dimension seed |

> Respect API terms, scraping restrictions, and rate limits for all providers. Platform menu APIs may be restricted; the external connector CSV is provided for compliant imports. The pipeline does not scrape restricted delivery platforms.

### Repeatable ingestion layer

Pipeline script: `scripts/live_pipeline.py`

Steps:
1. Source fetch (per-source success / failed / skipped state + latency timing)
2. Area + cuisine normalisation across all sources
3. Cross-source deduplication + fuzzy entity matching
4. Product dimension build with fuzzy dedup against seed catalogue
5. Data quality filtering (range, IQR outlier tagging)
6. Curated latest write to `data/curated/latest/`
7. Monitoring telemetry to `data/monitoring/`

### Deduplication and entity matching

- **Stable keys**: `Source_Record_ID` when available
- **Fuzzy match fallback**: weighted restaurant-name (75%) + area similarity (25%), threshold ≥ 88
- **Merge behaviour**: combine attributes into one canonical restaurant record
- **Confidence**: `Match_Confidence` stored per canonical record
- **Product dedup**: fuzzy similarity ≥ 85 on dish name merges inferred dishes back to seed

### Data quality rules

- Price parsing and numeric validation
- Invalid / out-of-range filtering (₹20–₹2,000)
- IQR-based outlier tagging (requires ≥ 5 samples per dish)
- Dish-name normalization (canonical naming via `standardize_dish_name`)
- `Price_Validation_Status` and confidence fields retained for audit

### Storage layout

```
data/
  curated/
    latest/           ← committed to Git; stable feed for Power BI & page
      Restaurant.csv
      Product.csv
      Fact_Menu_Price.csv
    history/          ← gitignored; write-only; available on runner only
  external/
    seed_restaurants.csv
    seed_products.csv
    seed_fact_menu_price.csv
    menu_prices.csv           (optional external connector)
    experience_submissions.csv
  monitoring/
    source_status.csv
    refresh_metrics.csv
    error_log.jsonl
  raw/                ← gitignored; write-only; available on runner only
```

### Monitoring and failure handling

| File | Columns |
|---|---|
| `data/monitoring/source_status.csv` | `run_timestamp, source, status, record_count, latency_ms, is_fallback, error` |
| `data/monitoring/refresh_metrics.csv` | `run_timestamp, pipeline_duration_ms, restaurant_count, product_count, fact_count, error_count, osm_record_count, google_record_count, seed_record_count, fallback_used` |
| `data/monitoring/error_log.jsonl` | One JSON object per line — captures both `failed` and `skipped` source events |

---

## Power BI and Live Page

### Power BI model

Use these curated files as the model input:
- `data/curated/latest/Restaurant.csv`
- `data/curated/latest/Product.csv`
- `data/curated/latest/Fact_Menu_Price.csv`

Set Power BI scheduled refresh against the curated latest layer so KPI visuals (avg / median / min / max and competitor comparisons) update automatically.

### Live GitHub Page

- Generated page: `docs/index.html`
- Build script: `scripts/build_pages.py`
- Auto-refreshed by: `.github/workflows/live-data-pipeline.yml`
- Default domain: `https://trambak001.github.io/data_restaurant/`
- Optional custom domain: set repository variable `PAGES_CUSTOM_DOMAIN` — workflow writes `docs/CNAME` automatically

### Community experience updates

The live page includes a **Share a field experience** link. A visitor can submit a restaurant experience, optional dish price, and a source URL through a GitHub Issue form. GitHub Actions validates the fields, stores the submission in `data/external/experience_submissions.csv`, and triggers a pipeline refresh.

---

## Repository Files

| File / Directory | Description |
|---|---|
| `scripts/live_pipeline.py` | Live ingestion, normalisation, matching, quality, and curated output builder |
| `scripts/build_pages.py` | Builds the live GitHub Pages dashboard from curated latest data |
| `scripts/ingest_experience_issue.py` | Parses and stores community GitHub Issue submissions |
| `.github/workflows/live-data-pipeline.yml` | Scheduled refresh workflow (12-hour cron + manual dispatch) |
| `.github/workflows/experience-submission.yml` | Community submission trigger workflow |
| `data/curated/latest/` | Latest cleaned tables — Power BI / live page feed |
| `data/external/seed_*.csv` | Seed dimension data (restaurants, products, historical prices) |
| `data/monitoring/` | Source status, refresh metrics, and error logs |
| `docs/index.html` | Published live market page |
| `requirements.txt` | Python dependencies |
| `LICENSE` | MIT license |

## Tools Used

- Python (pandas, requests)
- GitHub Actions
- Power BI
- OpenStreetMap / Overpass API
- Google Places API (optional)
