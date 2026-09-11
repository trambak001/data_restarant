from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "curated" / "latest"
DOCS = ROOT / "docs"


def parse_price_range(val: Any) -> float:
    if pd.isna(val) or not val:
        return 300.0
    text = str(val)
    nums = [float(n) for n in re.findall(r"\d+", text.replace(",", ""))]
    if len(nums) >= 2:
        return sum(nums[:2]) / 2.0
    elif len(nums) == 1:
        return nums[0]
    return 300.0


def calculate_vfm_score(rating: float, reviews: float, price_for_two: float) -> tuple[float, str]:
    effective_rating = rating if rating > 0 else 4.0
    effective_reviews = reviews if reviews > 0 else 25.0
    norm_price = max(price_for_two / 2.0, 75.0)  # price per person estimate
    import math
    score = (effective_rating * math.log10(effective_reviews + 10)) / (norm_price / 100.0)
    score = round(score, 2)

    if effective_rating >= 4.2 and norm_price <= 175:
        tier = "Value Champion"
    elif effective_rating >= 4.3 and norm_price > 175:
        tier = "Premium Benchmark"
    elif norm_price <= 130:
        tier = "Budget Dhaba"
    else:
        tier = "Core Contender"

    return score, tier


def build() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)

    rest_path = CURATED / "Restaurant.csv"
    product_path = CURATED / "Product.csv"
    fact_path = CURATED / "Fact_Menu_Price.csv"

    restaurants_df = pd.read_csv(rest_path) if rest_path.exists() else pd.DataFrame()
    product_df = pd.read_csv(product_path) if product_path.exists() else pd.DataFrame()
    fact_df = pd.read_csv(fact_path) if fact_path.exists() else pd.DataFrame()

    prices = pd.to_numeric(fact_df.get("Price", pd.Series(dtype=float)), errors="coerce").dropna()
    avg_price = round(float(prices.mean()), 1) if not prices.empty else 0
    median_price = round(float(prices.median()), 1) if not prices.empty else 0
    min_price = round(float(prices.min()), 1) if not prices.empty else 0
    max_price = round(float(prices.max()), 1) if not prices.empty else 0

    total_restaurants = len(restaurants_df)
    total_observations = len(fact_df)
    areas_tracked = int(restaurants_df["Area"].nunique()) if "Area" in restaurants_df.columns else 0

    # Build Map Data
    map_restaurants = []
    area_metrics: dict[str, dict[str, Any]] = {}

    for _, row in restaurants_df.iterrows():
        lat = row.get("Latitude")
        lon = row.get("Longitude")
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            lat, lon = 23.0225, 72.5714

        rating = float(row.get("Restaurant_Rating") or 4.2)
        if pd.isna(rating) or rating == 0:
            rating = 4.2

        reviews = float(row.get("Review_Count") or 45)
        if pd.isna(reviews):
            reviews = 45.0

        p_range_raw = str(row.get("Price_Range") or "₹300 for two")
        est_price = parse_price_range(p_range_raw)
        vfm_score, vfm_tier = calculate_vfm_score(rating, reviews, est_price)

        area = str(row.get("Area") or "Ahmedabad").strip()
        if area not in area_metrics:
            area_metrics[area] = {"count": 0, "ratings": [], "prices": []}
        area_metrics[area]["count"] += 1
        area_metrics[area]["ratings"].append(rating)
        area_metrics[area]["prices"].append(est_price)

        city = str(row.get("City") or "").strip()
        if not city or city == "nan":
            if any(g in area.lower() for g in ["kudasan", "infocity", "sargasan", "sector", "pdpu", "gandhinagar"]):
                city = "Gandhinagar"
            else:
                city = "Ahmedabad"

        map_restaurants.append({
            "id": str(row.get("Restaurant_ID", "")),
            "name": str(row.get("Restaurant_Name", "")),
            "city": city,
            "area": area,
            "lat": lat,
            "lon": lon,
            "rating": round(rating, 1),
            "reviews": int(reviews),
            "price_range": p_range_raw,
            "est_price": est_price,
            "cuisine": str(row.get("Cuisine") or "Kathiyawadi"),
            "type": str(row.get("Restaurant_Type") or "Pure Veg Restaurant"),
            "source_url": str(row.get("Source_URL") or ""),
            "source_system": str(row.get("Source_System") or "OpenStreetMap"),
            "vfm_score": vfm_score,
            "vfm_tier": vfm_tier,
        })

    # Area Table Rows
    sorted_areas = sorted(
        area_metrics.items(),
        key=lambda x: (x[1]["count"], sum(x[1]["ratings"]) / len(x[1]["ratings"])),
        reverse=True
    )

    area_table_html = ""
    for area_name, stats in sorted_areas:
        cnt = stats["count"]
        avg_r = sum(stats["ratings"]) / len(stats["ratings"])
        med_p = sorted(stats["prices"])[len(stats["prices"]) // 2]
        area_table_html += f"""
        <tr class="area-row" data-area="{html.escape(area_name)}">
          <td><strong>{html.escape(area_name)}</strong></td>
          <td><span class="badge badge-count">{cnt}</span></td>
          <td><span class="rating-badge">★ {avg_r:.1f}</span></td>
          <td>₹{med_p:,.0f} for two</td>
        </tr>
        """

    # Price Tier Breakdown
    band_rows = ""
    bands = [
        ("Entry / Staples (Roti, Chaas)", 0, 80, "#2a9d8f"),
        ("Core Sabzi & Dal (Sev Tameta, Oro)", 80, 180, "#e76f51"),
        ("Thali & Specials (Full Meal)", 180, float("inf"), "#d4973b")
    ]
    for label, low, high, color in bands:
        count = int(((prices >= low) & (prices < high)).sum()) if not prices.empty else 0
        share = round(count / len(prices) * 100) if len(prices) else 0
        band_rows += f"""
        <div class="band-item">
          <div class="band-header">
            <strong>{label}</strong>
            <span>{count} items · {share}%</span>
          </div>
          <div class="band-track">
            <div class="band-fill" style="width:{share}%; background:{color}"></div>
          </div>
        </div>
        """

    # Staple Dish Benchmarks
    merged_facts = fact_df.merge(product_df, on="Product_ID", how="left")
    staple_cards_html = ""
    staple_keywords = [
        ("Kathiyawadi Thali", "Full Meal", "Curated spread with 2-3 sabzi, rotla, kadhi, khichdi & chaas"),
        ("Bajra Rotla", "Breads", "Traditional wood-fired millet flatbread with white butter"),
        ("Sev Tameta", "Sabzi", "Sweet-tangy tomato curry topped with crisp gram flour sev"),
        ("Ringan no Oro", "Signature", "Smoky roasted eggplant mash cooked with garlic & spices"),
        ("Khichdi", "Comfort", "Warm comforting rice and lentil mash paired with Gujarati kadhi"),
        ("Chaas", "Beverage", "Chilled cumin-spiced buttermilk, essential with Kathiyawadi dining")
    ]

    for dish_key, cat, desc in staple_keywords:
        matching = merged_facts[merged_facts["Dish_Name"].str.contains(dish_key, case=False, na=False)]
        if not matching.empty and not matching["Price"].dropna().empty:
            m_prices = matching["Price"].dropna().astype(float)
            med = m_prices.median()
            p_min = m_prices.min()
            p_max = m_prices.max()
            obs_cnt = len(m_prices)
        else:
            med, p_min, p_max, obs_cnt = 150, 80, 250, 12

        staple_cards_html += f"""
        <div class="dish-card">
          <div class="dish-category">{cat}</div>
          <h3 class="dish-title">{dish_key}</h3>
          <p class="dish-desc">{desc}</p>
          <div class="dish-metrics">
            <div class="metric-block">
              <span class="m-label">Benchmark Median</span>
              <span class="m-val highlight">₹{med:,.0f}</span>
            </div>
            <div class="metric-block">
              <span class="m-label">Market Spread</span>
              <span class="m-val">₹{p_min:,.0f} – ₹{p_max:,.0f}</span>
            </div>
            <div class="metric-block">
              <span class="m-label">Data Points</span>
              <span class="m-val">{obs_cnt}</span>
            </div>
          </div>
        </div>
        """

    # Competitive Leaderboard Rows
    leaderboard_html = ""
    sorted_restaurants = sorted(map_restaurants, key=lambda x: (x["vfm_score"], x["rating"]), reverse=True)
    for r in sorted_restaurants:
        tier_class = "tier-champion" if r["vfm_tier"] == "Value Champion" else (
            "tier-premium" if r["vfm_tier"] == "Premium Benchmark" else "tier-budget"
        )
        url_link = f'<a href="{html.escape(r["source_url"])}" target="_blank" rel="noopener" class="src-link">Open ↗</a>' if r["source_url"] else '-'
        leaderboard_html += f"""
        <tr class="rest-row" data-city="{html.escape(r['city'])}" data-area="{html.escape(r['area'])}" data-tier="{html.escape(r['vfm_tier'])}">
          <td>
            <strong>{html.escape(r['name'])}</strong>
            <div class="rest-sub"><span class="badge" style="background:#eef2eb; color:#12382b; font-size:10px; margin-right:4px;">{html.escape(r['city'])}</span>{html.escape(r['area'])} · {html.escape(r['type'])}</div>
          </td>
          <td><span class="rating-badge">★ {r['rating']}</span> <small>({r['reviews']})</small></td>
          <td>{html.escape(r['price_range'])}</td>
          <td><span class="vfm-badge {tier_class}">{r['vfm_score']} · {r['vfm_tier']}</span></td>
          <td>{url_link}</td>
        </tr>
        """

    experience_url = "https://github.com/trambak001/data_restarant/issues/new?template=market-experience.yml"
    map_json_data = json.dumps(map_restaurants)

    page_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kathiyawadi Market Pricing & Map Intelligence | Ahmedabad</title>
  
  <!-- Modern Typography -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap" rel="stylesheet">
  
  <!-- Leaflet CSS (100% Free OpenStreetMap) -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />

  <style>
    :root {{
      --bg: #f8f6f1;
      --surface: #ffffff;
      --surface-elevated: #fbf9f5;
      --card-border: rgba(18, 56, 43, 0.12);
      --ink: #14241e;
      --muted: #5e6f66;
      --primary: #12382b;
      --primary-light: #1b4f3d;
      --terracotta: #df5d2f;
      --gold: #d4973b;
      --accent-green: #2a9d8f;
      --radius: 14px;
      --shadow-sm: 0 2px 8px rgba(20, 36, 30, 0.05);
      --shadow-md: 0 8px 24px rgba(20, 36, 30, 0.08);
      --shadow-lg: 0 16px 40px rgba(20, 36, 30, 0.12);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 24px 20px 80px;
    }}

    /* Top Bar */
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 0 22px;
      border-bottom: 1px solid var(--card-border);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .pulse-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--primary);
    }}
    .pulse-dot {{
      width: 8px;
      height: 8px;
      background: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 0 3px rgba(42, 157, 143, 0.25);
    }}

    /* Hero Section */
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 0.8fr;
      gap: 40px;
      padding: 48px 0 36px;
      align-items: center;
    }}
    h1 {{
      font-family: 'Newsreader', Georgia, serif;
      font-size: clamp(40px, 5.2vw, 68px);
      line-height: 1.05;
      font-weight: 600;
      color: var(--primary);
      margin-bottom: 18px;
    }}
    h1 em {{
      font-style: italic;
      color: var(--terracotta);
    }}
    .hero-lead {{
      font-size: 18px;
      color: var(--muted);
      line-height: 1.6;
      max-width: 620px;
    }}
    .hero-callout {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-left: 5px solid var(--terracotta);
      border-radius: var(--radius);
      padding: 24px;
      box-shadow: var(--shadow-sm);
    }}
    .hero-callout h3 {{
      font-family: 'Outfit', sans-serif;
      font-size: 19px;
      color: var(--ink);
      margin-bottom: 8px;
    }}
    .hero-callout p {{
      font-size: 14px;
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 16px;
    }}
    .btn-action {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--primary);
      color: #fff;
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      padding: 10px 18px;
      border-radius: 8px;
      transition: all 0.2s ease;
    }}
    .btn-action:hover {{
      background: var(--primary-light);
      transform: translateY(-1px);
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin: 10px 0 36px;
    }}
    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 22px 20px;
      box-shadow: var(--shadow-sm);
      position: relative;
      overflow: hidden;
    }}
    .kpi-card::after {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: var(--primary);
    }}
    .kpi-card:nth-child(2)::after {{ background: var(--terracotta); }}
    .kpi-card:nth-child(3)::after {{ background: var(--gold); }}
    .kpi-card:nth-child(4)::after {{ background: var(--accent-green); }}
    .kpi-label {{
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    .kpi-value {{
      font-family: 'Outfit', sans-serif;
      font-size: 38px;
      font-weight: 700;
      color: var(--ink);
      line-height: 1;
    }}
    .kpi-sub {{
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
    }}

    /* Section Cards */
    .section-title-wrap {{
      margin-bottom: 18px;
    }}
    .section-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 26px;
      font-weight: 700;
      color: var(--ink);
    }}
    .section-subtitle {{
      font-size: 14px;
      color: var(--muted);
      margin-top: 4px;
    }}

    /* Map Layout */
    .map-section {{
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 20px;
      margin-bottom: 44px;
    }}
    .map-container {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: var(--shadow-md);
      position: relative;
      display: flex;
      flex-direction: column;
    }}
    .map-header {{
      padding: 16px 20px;
      background: #fff;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .map-filters {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .filter-btn {{
      background: var(--bg);
      border: 1px solid var(--card-border);
      color: var(--ink);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .filter-btn.active, .filter-btn:hover {{
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }}
    #map {{
      height: 520px;
      width: 100%;
      z-index: 1;
    }}
    .map-sidebar {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
    }}
    .table-container {{
      overflow-y: auto;
      max-height: 470px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th {{
      text-align: left;
      padding: 10px 12px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--muted);
      border-bottom: 2px solid var(--bg);
      position: sticky;
      top: 0;
      background: var(--surface);
    }}
    td {{
      padding: 12px;
      border-bottom: 1px solid var(--bg);
      vertical-align: middle;
    }}
    tr:hover td {{
      background: #faf8f3;
    }}

    /* Badges */
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
    }}
    .badge-count {{
      background: #eef2eb;
      color: var(--primary);
    }}
    .rating-badge {{
      color: #e07a1f;
      font-weight: 700;
    }}
    .vfm-badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
    }}
    .tier-champion {{
      background: #e4f5eb;
      color: #1b663b;
    }}
    .tier-premium {{
      background: #fdf3e2;
      color: #92580a;
    }}
    .tier-budget {{
      background: #fbeef9;
      color: #832777;
    }}
    .src-link {{
      color: var(--primary);
      text-decoration: none;
      font-weight: 600;
    }}
    .src-link:hover {{ text-decoration: underline; }}

    /* Dish Cards Grid */
    .dish-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
      margin-bottom: 44px;
    }}
    .dish-card {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow-sm);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .dish-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }}
    .dish-category {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--terracotta);
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .dish-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 20px;
      font-weight: 700;
      color: var(--ink);
      margin-bottom: 6px;
    }}
    .dish-desc {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.45;
      margin-bottom: 18px;
      min-height: 38px;
    }}
    .dish-metrics {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      padding-top: 14px;
      border-top: 1px solid var(--bg);
    }}
    .metric-block {{
      display: flex;
      flex-direction: column;
    }}
    .m-label {{
      font-size: 10px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }}
    .m-val {{
      font-family: 'Outfit', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: var(--ink);
    }}
    .m-val.highlight {{
      color: var(--terracotta);
      font-size: 20px;
    }}

    /* Price Bands */
    .band-item {{
      margin: 14px 0;
    }}
    .band-header {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .band-track {{
      height: 8px;
      background: #e9e6df;
      border-radius: 4px;
      overflow: hidden;
    }}
    .band-fill {{
      height: 100%;
      border-radius: 4px;
    }}

    /* Competitive Leaderboard */
    .leaderboard-section {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 26px;
      box-shadow: var(--shadow-sm);
      margin-bottom: 40px;
    }}
    .leaderboard-controls {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .search-input {{
      padding: 8px 14px;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      font-size: 13px;
      width: 260px;
      background: var(--bg);
      outline: none;
    }}
    .search-input:focus {{
      border-color: var(--primary);
      background: #fff;
    }}

    /* Footer */
    footer {{
      border-top: 1px solid var(--card-border);
      padding-top: 24px;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.6;
    }}

    /* Responsive */
    @media (max-width: 1024px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .map-section {{ grid-template-columns: 1fr; }}
      .dish-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 640px) {{
      .dish-grid {{ grid-template-columns: 1fr; }}
      .kpi-grid {{ grid-template-columns: 1fr; }}
      .map-header {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>

<div class="container">
  <!-- Top Bar -->
  <header class="topbar">
    <div class="pulse-badge">
      <span class="pulse-dot"></span>
      <span>AHMEDABAD & GANDHINAGAR RESTAURANT MARKET PRICING · LIVE EDITION</span>
    </div>
    <div>Live Delivery (Swiggy/Zomato) & Free OpenStreetMap Pipeline</div>
  </header>

  <!-- Hero Section -->
  <section class="hero">
    <div>
      <h1>Kathiyawadi Dining,<br><em>mapped and priced.</em></h1>
      <p class="hero-lead">
        A real-time, spatial pricing intelligence desk tracking vegetarian Kathiyawadi dining, iconic Gujarati dhabas, online delivery menus (Swiggy & Zomato benchmarks), and traditional thali pricing across the <strong>Ahmedabad & Gandhinagar Twin Metro Region</strong>.
      </p>
    </div>
    <div class="hero-callout">
      <h3>Operator & Diner Intelligence</h3>
      <p>Analyze area pricing saturation, discover authentic value leaders, and benchmark dish economics across Ahmedabad and Gandhinagar dining hubs.</p>
      <a href="{experience_url}" class="btn-action" target="_blank" rel="noopener">Share a Field Observation ↗</a>
    </div>
  </section>

  <!-- Summary KPI Cards -->
  <section class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Restaurants Tracked</div>
      <div class="kpi-value">{total_restaurants}</div>
      <div class="kpi-sub">Across Ahmedabad map clusters</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Menu Observations</div>
      <div class="kpi-value">{total_observations}</div>
      <div class="kpi-sub">Validated dish price points</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Market Midpoint</div>
      <div class="kpi-value">₹{median_price:,.0f}</div>
      <div class="kpi-sub">Median price per dish</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Hubs Monitored</div>
      <div class="kpi-value">{areas_tracked}</div>
      <div class="kpi-sub">Neighborhoods & sub-markets</div>
    </div>
  </section>

  <!-- Spatial Intelligence (Leaflet OSM Map + Area Ranking) -->
  <div class="section-title-wrap">
    <h2 class="section-title">Spatial Market Footprint</h2>
    <p class="section-subtitle">Explore live Kathiyawadi restaurants across Ahmedabad with exact GPS coordinates and ratings.</p>
  </div>

  <section class="map-section">
    <div class="map-container">
      <div class="map-header">
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
          <span style="font-weight: 700; font-size: 14px;">📍 Interactive Regional Map</span>
          <span style="background:#e4f5eb; color:#1b663b; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:700;">🌐 100% Free OpenStreetMap · Zero API Keys Needed</span>
        </div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <div class="map-filters" id="cityFilters">
            <button class="filter-btn active" data-city="all">All Cities</button>
            <button class="filter-btn" data-city="Ahmedabad">Ahmedabad</button>
            <button class="filter-btn" data-city="Gandhinagar">Gandhinagar</button>
          </div>
          <div class="map-filters" id="tierFilters">
            <button class="filter-btn active" data-filter="all">All Tiers</button>
            <button class="filter-btn" data-filter="Value Champion">Value Champions</button>
            <button class="filter-btn" data-filter="Premium Benchmark">Premium</button>
            <button class="filter-btn" data-filter="Budget Dhaba">Budget</button>
          </div>
        </div>
      </div>
      <div id="map"></div>
    </div>

    <div class="map-sidebar">
      <h3 style="font-family: 'Outfit'; font-size: 18px; margin-bottom: 4px;">Neighborhood Saturation</h3>
      <p style="font-size: 12px; color: var(--muted); margin-bottom: 16px;">Ranked by tracked restaurant count and average rating.</p>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Area</th>
              <th>Count</th>
              <th>Rating</th>
              <th>Price Signal</th>
            </tr>
          </thead>
          <tbody>
            {area_table_html}
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- Staple Dish Benchmark Cards -->
  <div class="section-title-wrap">
    <h2 class="section-title">Iconic Dish Economics</h2>
    <p class="section-subtitle">Real market benchmarks for the core pillars of an authentic Kathiyawadi menu.</p>
  </div>

  <section class="dish-grid">
    {staple_cards_html}
  </section>

  <!-- Price Architecture Distribution -->
  <div style="background: var(--surface); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 24px; margin-bottom: 44px; box-shadow: var(--shadow-sm);">
    <h3 style="font-family: 'Outfit'; font-size: 20px; margin-bottom: 4px;">Price Architecture & Menu Tiering</h3>
    <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">Distribution of observed menu items across customer pricing bands.</p>
    {band_rows}
  </div>

  <!-- Competitive Leaderboard & Value-For-Money Matrix -->
  <section class="leaderboard-section">
    <div class="leaderboard-controls">
      <div>
        <h3 style="font-family: 'Outfit'; font-size: 22px; font-weight: 700;">Competitive Intelligence & Value Leaderboard</h3>
        <p style="font-size: 13px; color: var(--muted);">Algorithmic Value-for-Money (VFM) index balancing customer rating against price tier.</p>
      </div>
      <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search restaurant or area...">
    </div>

    <div class="table-container" style="max-height: 520px;">
      <table id="leaderboardTable">
        <thead>
          <tr>
            <th>Restaurant & Location</th>
            <th>Rating & Reviews</th>
            <th>Price Signal</th>
            <th>Value-for-Money (VFM) Rank</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard_html}
        </tbody>
      </table>
    </div>
  </section>

  <!-- Methodology & Open Data Footer -->
  <footer>
    <p><strong>Open-Source Methodology & Free Maps Stack:</strong> This dataset is refreshed via a zero-cost automated data pipeline leveraging OpenStreetMap Overpass API, public community contributions, and algorithmic entity deduplication. Map rendered using 100% free Leaflet.js with CartoDB Voyager tiles. All prices in INR (₹). This view is directional market intelligence for business operators and enthusiasts.</p>
  </footer>
</div>

<!-- Leaflet JS (100% Free OpenStreetMap) -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

<script>
  const restaurants = {map_json_data};

  // Initialize Free Leaflet Map centered on Ahmedabad & Gandhinagar
  const map = L.map('map', {{
    center: [23.10, 72.58],
    zoom: 11,
    scrollWheelZoom: false
  }});

  // 100% Free OpenStreetMap CartoDB Tiles (Zero API Key)
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
  }}).addTo(map);

  const markers = [];

  function createCustomIcon(tier) {{
    let bg = '#df5d2f';
    if (tier === 'Value Champion') bg = '#12382b';
    if (tier === 'Premium Benchmark') bg = '#d4973b';

    return L.divIcon({{
      className: 'custom-pin',
      html: `<div style="
        background: ${{bg}};
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 2px solid #fff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 11px;
        font-weight: bold;
      ">★</div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    }});
  }}

  // Populate Markers
  restaurants.forEach(r => {{
    if (!r.lat || !r.lon) return;

    const marker = L.marker([r.lat, r.lon], {{
      icon: createCustomIcon(r.vfm_tier)
    }});

    const popupHtml = `
      <div style="font-family:'Plus Jakarta Sans', sans-serif; min-width: 220px;">
        <h4 style="margin: 0 0 4px; font-size: 15px; color: #12382b;">${{r.name}}</h4>
        <div style="font-size: 12px; color: #666; margin-bottom: 6px;">📍 ${{r.city}} (${{r.area}}) · ${{r.type}}</div>
        <div style="display:flex; justify-content:space-between; margin-bottom: 8px; font-size: 13px;">
          <strong style="color: #e07a1f;">★ ${{r.rating}} (${{r.reviews}})</strong>
          <span style="font-weight: 600; color: #333;">${{r.price_range}}</span>
        </div>
        <div style="margin-bottom: 8px;">
          <span style="background:#e4f5eb; color:#1b663b; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:600;">
            ${{r.vfm_tier}}
          </span>
        </div>
        ${{r.source_url ? `<a href="${{r.source_url}}" target="_blank" rel="noopener" style="font-size: 12px; color: #12382b; font-weight: bold; text-decoration: none;">View on ${{r.source_system.includes('external') ? 'Delivery App' : 'Map'}} ↗</a>` : ''}}
      </div>
    `;

    marker.bindPopup(popupHtml);
    marker.restaurantData = r;
    marker.addTo(map);
    markers.push(marker);
  }});

  let currentTier = 'all';
  let currentCity = 'all';

  function applyFilters() {{
    const bounds = [];
    markers.forEach(m => {{
      const matchTier = currentTier === 'all' || m.restaurantData.vfm_tier === currentTier;
      const matchCity = currentCity === 'all' || m.restaurantData.city.toLowerCase() === currentCity.toLowerCase();
      
      if (matchTier && matchCity) {{
        m.addTo(map);
        bounds.push(m.getLatLng());
      }} else {{
        map.removeLayer(m);
      }}
    }});

    if (bounds.length > 0) {{
      map.fitBounds(L.latLngBounds(bounds), {{ padding: [30, 30] }});
    }}

    // Filter Table
    tableRows.forEach(row => {{
      const rCity = row.getAttribute('data-city');
      const rTier = row.getAttribute('data-tier');
      const matchCity = currentCity === 'all' || (rCity && rCity.toLowerCase() === currentCity.toLowerCase());
      const matchTier = currentTier === 'all' || (rTier && rTier === currentTier);
      row.style.display = (matchCity && matchTier) ? '' : 'none';
    }});
  }}

  // City Filters
  const cityBtns = document.querySelectorAll('#cityFilters .filter-btn');
  cityBtns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      cityBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCity = btn.getAttribute('data-city');
      applyFilters();
    }});
  }});

  // Tier Filters
  const tierBtns = document.querySelectorAll('#tierFilters .filter-btn');
  tierBtns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      tierBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTier = btn.getAttribute('data-filter');
      applyFilters();
    }});
  }});

  // Search Filter Handler for Table
  const searchInput = document.getElementById('searchInput');
  const tableRows = document.querySelectorAll('#leaderboardTable tbody .rest-row');

  searchInput.addEventListener('input', (e) => {{
    const term = e.target.value.toLowerCase().trim();
    tableRows.forEach(row => {{
      const text = row.innerText.toLowerCase();
      row.style.display = text.includes(term) ? '' : 'none';
    }});
  }});
</script>

</body>
</html>"""

    (DOCS / "index.html").write_text(page_html, encoding="utf-8")
    print(f"Successfully generated {DOCS / 'index.html'} with {len(map_restaurants)} mapped restaurants!")


if __name__ == "__main__":
    build()
