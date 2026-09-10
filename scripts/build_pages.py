from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated" / "latest"
DOCS = ROOT / "docs"


def build() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)

    rest_path = CURATED / "Restaurant.csv"
    fact_path = CURATED / "Fact_Menu_Price.csv"

    restaurants = pd.read_csv(rest_path) if rest_path.exists() else pd.DataFrame()
    fact = pd.read_csv(fact_path) if fact_path.exists() else pd.DataFrame()

    avg_price = round(float(fact["Price"].mean()), 2) if not fact.empty else 0
    median_price = round(float(fact["Price"].median()), 2) if not fact.empty else 0
    min_price = round(float(fact["Price"].min()), 2) if not fact.empty else 0
    max_price = round(float(fact["Price"].max()), 2) if not fact.empty else 0

    top_restaurants = ""
    if not restaurants.empty:
        cols = ["Restaurant_Name", "Area", "Restaurant_Rating", "Source_System"]
        available = [c for c in cols if c in restaurants.columns]
        top = restaurants[available].head(15).fillna("")
        rows = "\n".join(
            "<tr>" + "".join(f"<td>{str(v)}</td>" for v in row) + "</tr>" for row in top.values.tolist()
        )
        headers = "".join(f"<th>{c}</th>" for c in available)
        top_restaurants = f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Kathiyawadi Live Market Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f9fc; color: #1c2430; }}
    .kpis {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px,1fr)); gap:12px; margin:18px 0; }}
    .card {{ background:#fff; border:1px solid #dfe6ef; border-radius:8px; padding:12px; }}
    table {{ width:100%; border-collapse: collapse; background:#fff; }}
    th, td {{ border:1px solid #dfe6ef; text-align:left; padding:8px; }}
    th {{ background:#edf3fb; }}
  </style>
</head>
<body>
  <h1>Kathiyawadi Restaurant Live Market Page</h1>
  <p>Auto-updated by GitHub Actions from curated live data.</p>
  <div class=\"kpis\">
    <div class=\"card\"><strong>Restaurants</strong><br>{len(restaurants)}</div>
    <div class=\"card\"><strong>Menu Rows</strong><br>{len(fact)}</div>
    <div class=\"card\"><strong>Avg Price</strong><br>₹{avg_price}</div>
    <div class=\"card\"><strong>Median Price</strong><br>₹{median_price}</div>
    <div class=\"card\"><strong>Min Price</strong><br>₹{min_price}</div>
    <div class=\"card\"><strong>Max Price</strong><br>₹{max_price}</div>
  </div>
  <h2>Sample Restaurants</h2>
  {top_restaurants or '<p>No curated data available yet.</p>'}
  <p><small>Data source coverage: Ahmedabad vegetarian/Kathiyawadi restaurants from OpenStreetMap, optional Google Places, and optional external menu connectors.</small></p>
</body>
</html>"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    build()
