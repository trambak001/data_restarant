from __future__ import annotations

import html
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

    prices = pd.to_numeric(fact.get("Price", pd.Series(dtype=float)), errors="coerce").dropna()
    avg_price = round(float(prices.mean()), 2) if not prices.empty else 0
    median_price = round(float(prices.median()), 2) if not prices.empty else 0
    min_price = round(float(prices.min()), 2) if not prices.empty else 0
    max_price = round(float(prices.max()), 2) if not prices.empty else 0
    premium_share = round(float((prices > median_price).mean() * 100)) if not prices.empty else 0

    def esc(value: object) -> str:
      return html.escape(str(value or ""))

    def money(value: float) -> str:
      return f"₹{value:,.0f}"

    area_rows = "<tr><td colspan=\"3\">No area data available yet.</td></tr>"
    if not restaurants.empty and "Area" in restaurants.columns:
      area_data = (
        restaurants.assign(Area=restaurants["Area"].fillna("Unmapped"))
        .groupby("Area", as_index=False)
        .agg(Restaurants=("Restaurant_ID", "count"), Avg_Rating=("Restaurant_Rating", "mean"))
        .sort_values(["Restaurants", "Avg_Rating"], ascending=False)
        .head(6)
      )
      area_rows = "".join(
        f"<tr><td>{esc(row.Area)}</td><td>{int(row.Restaurants)}</td>"
        f"<td><span class=\"rating\">{row.Avg_Rating:.1f}</span></td></tr>"
        for row in area_data.itertuples()
      )

    restaurant_rows = "<tr><td colspan=\"4\">No restaurant data available yet.</td></tr>"
    if not restaurants.empty:
      ranked = restaurants.copy()
      ranked["Restaurant_Rating"] = pd.to_numeric(ranked.get("Restaurant_Rating"), errors="coerce")
      ranked["Review_Count"] = pd.to_numeric(ranked.get("Review_Count"), errors="coerce").fillna(0)
      ranked = ranked.sort_values(["Restaurant_Rating", "Review_Count"], ascending=False).head(8)
      restaurant_rows = "".join(
        f"<tr><td><strong>{esc(row.Restaurant_Name)}</strong><small>{esc(row.Area)}</small></td>"
        f"<td><span class=\"rating\">{row.Restaurant_Rating:.1f}</span></td>"
        f"<td>{int(row.Review_Count):,}</td><td>{esc(row.Price_Range) or 'Not listed'}</td></tr>"
        for row in ranked.itertuples()
      )

    band_rows = ""
    bands = [("Entry", 0, 100), ("Core", 100, 250), ("Premium", 250, float("inf"))]
    for label, low, high in bands:
      count = int(((prices >= low) & (prices < high)).sum()) if not prices.empty else 0
      share = round(count / len(prices) * 100) if prices.size else 0
      band_rows += f"<div class=\"band\"><div><strong>{label}</strong><span>{count} dishes · {share}%</span></div>"
      band_rows += f"<div class=\"bar\"><i style=\"width:{share}%\"></i></div></div>"

    source_label = " + ".join(sorted(str(value) for value in restaurants.get("Source_System", pd.Series(dtype=str)).dropna().unique()))
    recommendation = (
      f"The market midpoint is {money(median_price)} across {len(prices):,} menu observations. "
      f"{premium_share}% of listed dishes sit above that midpoint, suggesting room for a clear value tier before premium pricing."
      if not prices.empty else "The next refresh will populate the market recommendation once validated menu prices arrive."
    )
    experience_url = "https://github.com/trambak001/data_restarant/issues/new?template=market-experience.yml"

    page = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Ahmedabad Market Brief | Kathiyawadi</title>
  <style>
    :root {{ --ink:#16231f; --muted:#6b7770; --paper:#f4f1e9; --card:#fffdf8; --green:#174d3d; --lime:#c5dc68; --orange:#e77c43; --line:#d9ded2; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); background:var(--paper); font-family: Georgia, 'Times New Roman', serif; }}
    .shell {{ max-width:1240px; margin:auto; padding:34px 28px 60px; }}
    .topline {{ display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--line); padding-bottom:18px; font-family:Arial,sans-serif; font-size:12px; letter-spacing:1.5px; text-transform:uppercase; color:var(--muted); }}
    .mark {{ color:var(--green); font-weight:bold; }} .hero {{ display:grid; grid-template-columns:1.45fr .8fr; gap:48px; padding:62px 0 44px; align-items:end; }}
    h1 {{ font-size:clamp(42px,6vw,78px); line-height:.92; letter-spacing:-2px; font-weight:normal; margin:0 0 22px; max-width:720px; }}
    .dek {{ max-width:620px; color:var(--muted); font:17px/1.6 Arial,sans-serif; }} .stamp {{ border-left:4px solid var(--orange); padding:4px 0 4px 18px; font:13px/1.5 Arial,sans-serif; color:var(--muted); }}
    .stamp strong {{ display:block; color:var(--ink); font:24px Georgia,serif; margin-bottom:5px; }} .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:38px; }}
    .kpi {{ background:var(--green); color:#fff; padding:22px 20px; min-height:126px; }} .kpi:nth-child(2) {{ background:var(--lime); color:var(--ink); }} .kpi:nth-child(3) {{ background:var(--orange); }}
    .kpi label {{ display:block; font:11px Arial,sans-serif; letter-spacing:1.2px; text-transform:uppercase; opacity:.75; }} .kpi strong {{ display:block; font-size:34px; font-weight:normal; margin-top:18px; }}
    .grid {{ display:grid; grid-template-columns:1.25fr .75fr; gap:18px; margin-bottom:18px; }} .panel {{ background:var(--card); border:1px solid var(--line); padding:26px; }}
    .panel h2 {{ font-size:25px; font-weight:normal; margin:0 0 6px; }} .sub {{ color:var(--muted); font:12px Arial,sans-serif; margin:0 0 22px; }}
    .recommend {{ background:#dfe8bb; border:0; }} .recommend h2 {{ color:var(--green); }} .recommend p {{ font-size:20px; line-height:1.35; margin:26px 0 0; }}
    .band {{ margin:20px 0; font:13px Arial,sans-serif; }} .band div:first-child {{ display:flex; justify-content:space-between; margin-bottom:8px; }} .band span {{ color:var(--muted); }} .bar {{ height:10px; background:#e6e8de; }} .bar i {{ display:block; height:100%; background:var(--orange); }}
    table {{ width:100%; border-collapse:collapse; font:13px Arial,sans-serif; }} th {{ color:var(--muted); font-size:10px; letter-spacing:1px; text-transform:uppercase; text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); }} td {{ padding:13px 8px; border-bottom:1px solid var(--line); vertical-align:top; }} td small {{ display:block; color:var(--muted); margin-top:4px; }} .rating {{ color:var(--orange); font-weight:bold; }}
    .footer {{ color:var(--muted); font:11px Arial,sans-serif; border-top:1px solid var(--line); padding-top:18px; margin-top:32px; }}
    .contribute {{ display:inline-block; margin-top:18px; padding:12px 16px; background:var(--green); color:#fff; text-decoration:none; font:12px Arial,sans-serif; letter-spacing:.4px; }}
    @media (max-width:760px) {{ .shell {{ padding:22px 16px 40px; }} .hero,.grid {{ grid-template-columns:1fr; gap:24px; }} .hero {{ padding:42px 0 30px; }} .kpis {{ grid-template-columns:repeat(2,1fr); }} .kpi strong {{ font-size:28px; }} .panel {{ padding:20px 16px; }} table {{ min-width:540px; }} .table-wrap {{ overflow:auto; }} }}
  </style>
</head>
<body>
  <main class=\"shell\">
    <div class=\"topline\"><span class=\"mark\">FIELDNOTE / AHMEDABAD</span><span>Market intelligence desk · Live edition</span></div>
    <section class=\"hero\"><div><h1>Kathiyawadi,<br><em>priced clearly.</em></h1><p class=\"dek\">A concise view of the Ahmedabad vegetarian dining market, built for operators, investors and teams deciding what to launch next.</p></div><div class=\"stamp\"><strong>Read the market</strong>Use the midpoint to frame your offer, the area mix to choose where to compete, and the leaders to understand the bar.<br><a class=\"contribute\" href=\"{experience_url}\">Share a field experience ↗</a></div></section>
    <section class=\"kpis\"><div class=\"kpi\"><label>Restaurants tracked</label><strong>{len(restaurants):,}</strong></div><div class=\"kpi\"><label>Menu observations</label><strong>{len(prices):,}</strong></div><div class=\"kpi\"><label>Market midpoint</label><strong>{money(median_price)}</strong></div><div class=\"kpi\"><label>Observed range</label><strong>{money(min_price)}–{money(max_price)}</strong></div></section>
    <section class=\"grid\"><article class=\"panel recommend\"><h2>Analyst's read</h2><p>{esc(recommendation)}</p></article><article class=\"panel\"><h2>Price architecture</h2><p class=\"sub\">Share of validated dishes by customer-facing tier</p>{band_rows}</article></section>
    <section class=\"grid\"><article class=\"panel\"><h2>Where the market clusters</h2><p class=\"sub\">Restaurant footprint by Ahmedabad area</p><div class=\"table-wrap\"><table><thead><tr><th>Area</th><th>Restaurants</th><th>Avg rating</th></tr></thead><tbody>{area_rows}</tbody></table></div></article><article class=\"panel\"><h2>Signal to watch</h2><p class=\"sub\">What is shaping this edition</p><p style=\"font-size:18px;line-height:1.45\">The strongest competitive signal is not the highest price. It is a credible combination of rating, local presence and a menu that lands near the market midpoint.</p><p class=\"sub\">Sources: {esc(source_label) or 'Pending refresh'}</p><p class=\"sub\">Maps and public menu connectors refresh automatically. Community observations are checked, then included in the next run.</p></article></section>
    <section class=\"panel\"><h2>Competitive set</h2><p class=\"sub\">Highest-rated tracked operators, with review depth for context</p><div class=\"table-wrap\"><table><thead><tr><th>Restaurant</th><th>Rating</th><th>Reviews</th><th>Price signal</th></tr></thead><tbody>{restaurant_rows}</tbody></table></div></section>
    <p class=\"footer\">Updated by the live data pipeline · Coverage: Ahmedabad vegetarian / Kathiyawadi restaurants · Prices shown in INR · This view is directional market intelligence, not a consumer ranking.</p>
  </main>
</body>
</html>"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build()
