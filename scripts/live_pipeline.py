from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_LATEST_DIR = DATA_DIR / "curated" / "latest"
CURATED_HISTORY_DIR = DATA_DIR / "curated" / "history"
MONITORING_DIR = DATA_DIR / "monitoring"
EXTERNAL_DIR = DATA_DIR / "external"

RESTAURANT_COLUMNS = [
    "Restaurant_ID",
    "Restaurant_Name",
    "City",
    "Area",
    "Restaurant_Type",
    "Cuisine",
    "Restaurant_Rating",
    "Review_Count",
    "Price_Range",
    "Source_URL",
    "Source_System",
    "Source_Record_ID",
    "Fetch_Time",
    "Match_Confidence",
]

PRODUCT_COLUMNS = [
    "Product_ID",
    "Dish_Name",
    "Food_Category",
    "Sub_Category",
    "Cuisine_Type",
    "Cooking_Medium",
]

FACT_COLUMNS = [
    "Menu_Price_ID",
    "Restaurant_ID",
    "Product_ID",
    "Price",
    "Portion_Size",
    "Serving_Unit",
    "Dish_rating",
    "Menu_Type",
    "Source_URL",
    "Price_Date",
    "Fetch_Time",
    "Source_System",
    "Price_Validation_Status",
]


@dataclass
class SourceResult:
    name: str
    status: str
    record_count: int
    error: str | None
    restaurants: list[dict[str, Any]]
    menus: list[dict[str, Any]]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace("₹", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio() * 100


def read_all_excel_sheets(path: Path) -> dict[str, pd.DataFrame]:
    if not path.exists():
        return {}
    try:
        sheets = pd.read_excel(path, sheet_name=None)
        return {name: df for name, df in sheets.items()}
    except Exception:
        return {}


def load_products() -> pd.DataFrame:
    product_path = ROOT / "product.xlsx"
    if product_path.exists():
        try:
            product_df = pd.read_excel(product_path)
            if set(["Dish_Name"]).issubset(product_df.columns):
                return product_df
        except Exception:
            pass
    return pd.DataFrame(columns=PRODUCT_COLUMNS)


def load_historical_prices() -> pd.DataFrame:
    market_path = ROOT / "Kathiyawadi_Market_Data.xlsx"
    sheets = read_all_excel_sheets(market_path)
    fact_candidates: list[pd.DataFrame] = []
    for _, df in sheets.items():
        cols = {c.lower() for c in df.columns}
        if "price" in cols and ("dish_name" in cols or "product_id" in cols):
            fact_candidates.append(df)
    if not fact_candidates:
        return pd.DataFrame(columns=["Dish_Name", "Price"])

    joined = pd.concat(fact_candidates, ignore_index=True)
    if "Dish_Name" not in joined.columns and "Product_ID" in joined.columns:
        products = load_products()
        if "Product_ID" in products.columns and "Dish_Name" in products.columns:
            joined = joined.merge(products[["Product_ID", "Dish_Name"]], on="Product_ID", how="left")

    if "Dish_Name" not in joined.columns:
        return pd.DataFrame(columns=["Dish_Name", "Price"])

    joined["Price"] = joined["Price"].apply(safe_float)
    joined = joined.dropna(subset=["Dish_Name", "Price"])
    if joined.empty:
        return pd.DataFrame(columns=["Dish_Name", "Price"])

    return (
        joined.groupby("Dish_Name", as_index=False)["Price"]
        .median()
        .rename(columns={"Price": "Median_Price"})
    )


def fetch_osm_restaurants(timeout: int = 40) -> SourceResult:
    endpoint = "https://overpass-api.de/api/interpreter"
    query = """
[out:json][timeout:35];
area["name"="Ahmedabad"]["boundary"="administrative"]->.searchArea;
(
  node["amenity"="restaurant"](area.searchArea);
  way["amenity"="restaurant"](area.searchArea);
  relation["amenity"="restaurant"](area.searchArea);
);
out center tags;
""".strip()
    source_name = "openstreetmap_overpass"

    try:
        response = requests.post(endpoint, data=query, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        elements = payload.get("elements", [])
        restaurants: list[dict[str, Any]] = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name:
                continue
            cuisine = tags.get("cuisine", "")
            if "veg" not in cuisine.lower() and "kathiyawadi" not in cuisine.lower():
                if "vegetarian" not in tags.get("diet:vegetarian", "").lower():
                    continue
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            restaurants.append(
                {
                    "Restaurant_Name": name,
                    "City": "Ahmedabad",
                    "Area": tags.get("addr:suburb") or tags.get("addr:street") or "Ahmedabad",
                    "Restaurant_Type": "Vegetarian",
                    "Cuisine": cuisine or "Kathiyawadi",
                    "Restaurant_Rating": None,
                    "Review_Count": None,
                    "Price_Range": tags.get("price", ""),
                    "Source_URL": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
                    "Source_Record_ID": f"osm_{el.get('type')}_{el.get('id')}",
                    "Source_System": source_name,
                    "Latitude": lat,
                    "Longitude": lon,
                }
            )

        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(restaurants),
            error=None,
            restaurants=restaurants,
            menus=[],
        )
    except Exception as exc:
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
        )


def fetch_google_places(timeout: int = 40) -> SourceResult:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    source_name = "google_places"
    if not api_key:
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="GOOGLE_PLACES_API_KEY is not set",
            restaurants=[],
            menus=[],
        )

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    query = "vegetarian kathiyawadi restaurant in Ahmedabad"
    restaurants: list[dict[str, Any]] = []

    try:
        token: str | None = None
        for _ in range(3):
            params = {"key": api_key, "query": query}
            if token:
                params = {"key": api_key, "pagetoken": token}
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()

            for item in payload.get("results", []):
                restaurants.append(
                    {
                        "Restaurant_Name": item.get("name"),
                        "City": "Ahmedabad",
                        "Area": (item.get("formatted_address") or "Ahmedabad").split(",")[0],
                        "Restaurant_Type": "Vegetarian",
                        "Cuisine": "Kathiyawadi",
                        "Restaurant_Rating": item.get("rating"),
                        "Review_Count": item.get("user_ratings_total"),
                        "Price_Range": item.get("price_level"),
                        "Source_URL": f"https://maps.google.com/?cid={item.get('place_id')}",
                        "Source_Record_ID": item.get("place_id"),
                        "Source_System": source_name,
                        "Latitude": item.get("geometry", {}).get("location", {}).get("lat"),
                        "Longitude": item.get("geometry", {}).get("location", {}).get("lng"),
                    }
                )

            token = payload.get("next_page_token")
            if not token:
                break

        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(restaurants),
            error=None,
            restaurants=restaurants,
            menus=[],
        )
    except Exception as exc:
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
        )


def load_external_menu_file() -> SourceResult:
    source_name = "external_menu_csv"
    csv_path = EXTERNAL_DIR / "menu_prices.csv"
    if not csv_path.exists():
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="data/external/menu_prices.csv not found",
            restaurants=[],
            menus=[],
        )

    try:
        df = pd.read_csv(csv_path)
        required = {"Restaurant_Name", "Dish_Name", "Price", "Area", "Source_URL"}
        missing = sorted(required - set(df.columns))
        if missing:
            return SourceResult(
                name=source_name,
                status="failed",
                record_count=0,
                error=f"Missing columns: {', '.join(missing)}",
                restaurants=[],
                menus=[],
            )

        restaurants = []
        menus = []
        for idx, row in df.iterrows():
            rid = f"external_{idx}_{normalize_text(row['Restaurant_Name']).replace(' ', '_')}"
            restaurants.append(
                {
                    "Restaurant_Name": row["Restaurant_Name"],
                    "City": row.get("City", "Ahmedabad"),
                    "Area": row.get("Area", "Ahmedabad"),
                    "Restaurant_Type": row.get("Restaurant_Type", "Vegetarian"),
                    "Cuisine": row.get("Cuisine", "Kathiyawadi"),
                    "Restaurant_Rating": safe_float(row.get("Restaurant_Rating")),
                    "Review_Count": safe_float(row.get("Review_Count")),
                    "Price_Range": row.get("Price_Range", ""),
                    "Source_URL": row.get("Source_URL", ""),
                    "Source_Record_ID": rid,
                    "Source_System": source_name,
                }
            )
            menus.append(
                {
                    "Source_Record_ID": rid,
                    "Dish_Name": row["Dish_Name"],
                    "Price": safe_float(row["Price"]),
                    "Portion_Size": row.get("Portion_Size", "Regular"),
                    "Serving_Unit": row.get("Serving_Unit", "Plate"),
                    "Menu_Type": row.get("Menu_Type", "Main Course"),
                    "Source_URL": row.get("Source_URL", ""),
                    "Source_System": source_name,
                }
            )

        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(menus),
            error=None,
            restaurants=restaurants,
            menus=menus,
        )
    except Exception as exc:
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
        )


def load_experience_submissions() -> SourceResult:
    source_name = "community_experience"
    csv_path = EXTERNAL_DIR / "experience_submissions.csv"
    if not csv_path.exists():
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="data/external/experience_submissions.csv not found",
            restaurants=[],
            menus=[],
        )

    try:
        df = pd.read_csv(csv_path).fillna("")
        restaurants: list[dict[str, Any]] = []
        menus: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            if str(row.get("Status", "")).lower() not in {"validated", "pending_review"}:
                continue
            name = str(row.get("Restaurant_Name", "")).strip()
            area = str(row.get("Area", "Ahmedabad")).strip() or "Ahmedabad"
            if not name:
                continue
            issue_number = str(row.get("Issue_Number", "")).strip()
            source_url = str(row.get("Source_URL", "")).strip() or (
                f"https://github.com/trambak001/data_restarant/issues/{issue_number}"
                if issue_number else ""
            )
            restaurants.append(
                {
                    "Restaurant_Name": name,
                    "City": "Ahmedabad",
                    "Area": area,
                    "Restaurant_Type": "Vegetarian",
                    "Cuisine": "Kathiyawadi",
                    "Restaurant_Rating": safe_float(row.get("Experience_Rating")),
                    "Review_Count": 1,
                    "Price_Range": "",
                    "Source_URL": source_url,
                    "Source_Record_ID": f"experience_{issue_number or normalize_text(name)}",
                    "Source_System": source_name,
                }
            )
            dish_name = str(row.get("Dish_Name", "")).strip()
            dish_price = safe_float(row.get("Dish_Price"))
            if dish_name and dish_price is not None:
                menus.append(
                    {
                        "Source_Record_ID": f"experience_{issue_number or normalize_text(name)}",
                        "Dish_Name": dish_name,
                        "Price": dish_price,
                        "Portion_Size": "As observed",
                        "Serving_Unit": "Plate",
                        "Menu_Type": "Community observation",
                        "Source_URL": source_url,
                        "Source_System": source_name,
                    }
                )

        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(restaurants),
            error=None,
            restaurants=restaurants,
            menus=menus,
        )
    except Exception as exc:
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
        )


def load_local_seed_source() -> SourceResult:
    source_name = "kathiyawadi_seed_workbook"
    market_path = ROOT / "Kathiyawadi_Market_Data.xlsx"
    product_path = ROOT / "product.xlsx"
    if not market_path.exists():
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="Kathiyawadi_Market_Data.xlsx not found",
            restaurants=[],
            menus=[],
        )

    try:
        rest_df = pd.read_excel(market_path, sheet_name="Restaurant")
        fact_df = pd.read_excel(market_path, sheet_name="Fact_Menu_Price")
        prod_df = pd.read_excel(product_path) if product_path.exists() else pd.DataFrame(columns=["Product_ID", "Dish_Name"])
        if "Dish_Name" not in prod_df.columns:
            prod_df["Dish_Name"] = ""
        if "Product_ID" not in prod_df.columns:
            prod_df["Product_ID"] = ""

        restaurants = []
        for idx, row in rest_df.iterrows():
            src_id = f"seed_{row.get('Restaurant_ID', idx + 1)}"
            restaurants.append(
                {
                    "Restaurant_Name": row.get("Restaurant_Name", ""),
                    "City": row.get("City", "Ahmedabad"),
                    "Area": row.get("Area", "Ahmedabad"),
                    "Restaurant_Type": row.get("Restaurant_Type", "Vegetarian"),
                    "Cuisine": row.get("Cuisine", "Kathiyawadi"),
                    "Restaurant_Rating": safe_float(row.get("Restaurant_Rating")),
                    "Review_Count": safe_float(row.get("Review_Count")),
                    "Price_Range": row.get("Price_Range", ""),
                    "Source_URL": row.get("Source_URL", ""),
                    "Source_Record_ID": src_id,
                    "Source_System": source_name,
                }
            )

        rid_map = {
            str(row.get("Restaurant_ID")): f"seed_{row.get('Restaurant_ID')}"
            for _, row in rest_df.iterrows()
        }
        dish_map = {str(row.get("Product_ID")): row.get("Dish_Name", "") for _, row in prod_df.iterrows()}

        menus = []
        for _, row in fact_df.iterrows():
            menus.append(
                {
                    "Source_Record_ID": rid_map.get(str(row.get("Restaurant_ID")), ""),
                    "Dish_Name": dish_map.get(str(row.get("Product_ID")), ""),
                    "Price": safe_float(row.get("Price")),
                    "Portion_Size": row.get("Portion_Size", "Regular"),
                    "Serving_Unit": row.get("Serving_Unit", "Plate"),
                    "Dish_rating": safe_float(row.get("Dish_rating")),
                    "Menu_Type": row.get("Menu_Type", "Main Course"),
                    "Source_URL": row.get("Source_URL", ""),
                    "Source_System": source_name,
                    "Price_Date": row.get("Price_Date"),
                }
            )

        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(restaurants) + len(menus),
            error=None,
            restaurants=restaurants,
            menus=menus,
        )
    except Exception as exc:
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
        )


def deduplicate_restaurants(restaurants: pd.DataFrame) -> pd.DataFrame:
    canonical: list[dict[str, Any]] = []
    for record in restaurants.to_dict("records"):
        matched_index = None
        confidence = 100.0
        for i, existing in enumerate(canonical):
            if record.get("Source_Record_ID") and record.get("Source_Record_ID") == existing.get("Source_Record_ID"):
                matched_index = i
                confidence = 100.0
                break

            name_score = similarity(record.get("Restaurant_Name", ""), existing.get("Restaurant_Name", ""))
            area_score = similarity(record.get("Area", ""), existing.get("Area", ""))
            blended = (name_score * 0.75) + (area_score * 0.25)
            if blended >= 88:
                matched_index = i
                confidence = blended
                break

        if matched_index is None:
            record["Match_Confidence"] = 100.0
            canonical.append(record)
        else:
            existing = canonical[matched_index]
            if pd.isna(existing.get("Restaurant_Rating")) and pd.notna(record.get("Restaurant_Rating")):
                existing["Restaurant_Rating"] = record.get("Restaurant_Rating")
            if pd.isna(existing.get("Review_Count")) and pd.notna(record.get("Review_Count")):
                existing["Review_Count"] = record.get("Review_Count")
            if not existing.get("Source_URL") and record.get("Source_URL"):
                existing["Source_URL"] = record.get("Source_URL")
            existing["Match_Confidence"] = max(float(existing.get("Match_Confidence", 0)), float(confidence))

    if not canonical:
        return pd.DataFrame(columns=RESTAURANT_COLUMNS)

    df = pd.DataFrame(canonical)
    df.insert(0, "Restaurant_ID", [f"R{i+1:04d}" for i in range(len(df))])
    return df


def standardize_dish_name(name: str) -> str:
    n = normalize_text(name)
    mapping = {
        "sev tameta": "Sev Tameta",
        "sev tamatar": "Sev Tameta",
        "ringan no oro": "Ringan no Oro",
        "rotla": "Bajra Rotla",
        "khichadi": "Khichdi",
    }
    if n in mapping:
        return mapping[n]
    return " ".join(part.capitalize() for part in n.split())


def build_products(product_seed: pd.DataFrame, menu_df: pd.DataFrame) -> pd.DataFrame:
    seeds = []
    if not product_seed.empty:
        seed = product_seed.copy()
        for column in PRODUCT_COLUMNS:
            if column not in seed.columns:
                seed[column] = ""
        seeds = seed[PRODUCT_COLUMNS].to_dict("records")

    inferred = []
    for dish in sorted(set(menu_df.get("Dish_Name", []))):
        normalized = standardize_dish_name(dish)
        inferred.append(
            {
                "Product_ID": "",
                "Dish_Name": normalized,
                "Food_Category": "Main Course",
                "Sub_Category": "Kathiyawadi",
                "Cuisine_Type": "Kathiyawadi",
                "Cooking_Medium": "",
            }
        )

    combined = pd.DataFrame(seeds + inferred)
    if combined.empty:
        return pd.DataFrame(columns=PRODUCT_COLUMNS)

    combined["Dish_Name"] = combined["Dish_Name"].apply(standardize_dish_name)
    combined = combined.drop_duplicates(subset=["Dish_Name"], keep="first").reset_index(drop=True)
    combined["Product_ID"] = [f"P{i+1:04d}" for i in range(len(combined))]
    return combined[PRODUCT_COLUMNS]


def fallback_menu_from_medians(restaurants_df: pd.DataFrame, medians: pd.DataFrame) -> pd.DataFrame:
    if restaurants_df.empty or medians.empty:
        return pd.DataFrame(columns=["Restaurant_ID", "Dish_Name", "Price", "Source_URL", "Source_System", "Price_Date"]) 

    rows: list[dict[str, Any]] = []
    for _, rest in restaurants_df.iterrows():
        for _, dish in medians.head(12).iterrows():
            rows.append(
                {
                    "Restaurant_ID": rest["Restaurant_ID"],
                    "Dish_Name": dish["Dish_Name"],
                    "Price": safe_float(dish["Median_Price"]),
                    "Portion_Size": "Regular",
                    "Serving_Unit": "Plate",
                    "Dish_rating": None,
                    "Menu_Type": "Main Course",
                    "Source_URL": rest.get("Source_URL", ""),
                    "Source_System": "historical_benchmark_fallback",
                    "Price_Date": now_utc().date().isoformat(),
                }
            )
    return pd.DataFrame(rows)


def quality_filter_prices(fact_df: pd.DataFrame) -> pd.DataFrame:
    if fact_df.empty:
        return fact_df

    fact_df["Price"] = fact_df["Price"].apply(safe_float)
    fact_df["Price_Validation_Status"] = "ok"

    invalid_mask = fact_df["Price"].isna() | (fact_df["Price"] <= 0)
    fact_df.loc[invalid_mask, "Price_Validation_Status"] = "invalid"

    plausible_mask = (fact_df["Price"] >= 20) & (fact_df["Price"] <= 2000)
    fact_df.loc[~plausible_mask & ~invalid_mask, "Price_Validation_Status"] = "out_of_range"

    valid_prices = fact_df.loc[fact_df["Price_Validation_Status"] == "ok", "Price"]
    if not valid_prices.empty:
        q1 = valid_prices.quantile(0.25)
        q3 = valid_prices.quantile(0.75)
        iqr = q3 - q1
        low = q1 - (1.5 * iqr)
        high = q3 + (1.5 * iqr)
        outlier_mask = (fact_df["Price"] < low) | (fact_df["Price"] > high)
        fact_df.loc[outlier_mask & (fact_df["Price_Validation_Status"] == "ok"), "Price_Validation_Status"] = "iqr_outlier"

    return fact_df[fact_df["Price_Validation_Status"].isin(["ok", "iqr_outlier"])].reset_index(drop=True)


def ensure_dirs() -> None:
    for d in [RAW_DIR, CURATED_LATEST_DIR, CURATED_HISTORY_DIR, MONITORING_DIR, EXTERNAL_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def write_source_snapshots(timestamp: str, sources: list[SourceResult]) -> None:
    run_dir = RAW_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    for src in sources:
        path = run_dir / f"{src.name}.json"
        payload = {
            "name": src.name,
            "status": src.status,
            "record_count": src.record_count,
            "error": src.error,
            "restaurants": src.restaurants,
            "menus": src.menus,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def append_monitoring(timestamp: str, source_rows: list[dict[str, Any]], row_count: dict[str, int], errors: list[dict[str, Any]]) -> None:
    source_status_path = MONITORING_DIR / "source_status.csv"
    source_df = pd.DataFrame(source_rows)
    source_df["run_timestamp"] = timestamp

    if source_status_path.exists():
        prev = pd.read_csv(source_status_path)
        source_df = pd.concat([prev, source_df], ignore_index=True)
    source_df.to_csv(source_status_path, index=False)

    metrics = {
        "run_timestamp": timestamp,
        "restaurant_count": row_count.get("restaurant", 0),
        "product_count": row_count.get("product", 0),
        "fact_count": row_count.get("fact", 0),
        "error_count": len(errors),
    }

    metrics_path = MONITORING_DIR / "refresh_metrics.csv"
    metrics_df = pd.DataFrame([metrics])
    if metrics_path.exists():
        prev = pd.read_csv(metrics_path)
        metrics_df = pd.concat([prev, metrics_df], ignore_index=True)
    metrics_df.to_csv(metrics_path, index=False)

    if errors:
        error_path = MONITORING_DIR / "error_log.jsonl"
        with error_path.open("a", encoding="utf-8") as f:
            for error in errors:
                f.write(json.dumps(error, ensure_ascii=False) + "\n")


def save_curated(timestamp: str, restaurant_df: pd.DataFrame, product_df: pd.DataFrame, fact_df: pd.DataFrame) -> None:
    history_dir = CURATED_HISTORY_DIR / timestamp
    history_dir.mkdir(parents=True, exist_ok=True)

    for out_dir in [CURATED_LATEST_DIR, history_dir]:
        restaurant_df[RESTAURANT_COLUMNS].to_csv(out_dir / "Restaurant.csv", index=False)
        product_df[PRODUCT_COLUMNS].to_csv(out_dir / "Product.csv", index=False)
        fact_df[FACT_COLUMNS].to_csv(out_dir / "Fact_Menu_Price.csv", index=False)


def run_pipeline() -> None:
    ensure_dirs()
    run_time = now_utc()
    timestamp = run_time.strftime("%Y%m%d_%H%M%S")

    source_results = [
        load_local_seed_source(),
        fetch_osm_restaurants(),
        fetch_google_places(),
        load_external_menu_file(),
        load_experience_submissions(),
    ]

    write_source_snapshots(timestamp, source_results)

    source_rows = []
    errors = []
    restaurant_rows = []
    menu_rows = []

    for src in source_results:
        source_rows.append(
            {
                "source": src.name,
                "status": src.status,
                "record_count": src.record_count,
                "error": src.error or "",
            }
        )
        if src.status == "failed":
            errors.append({"run_timestamp": timestamp, "source": src.name, "error": src.error})

        restaurant_rows.extend(src.restaurants)
        menu_rows.extend(src.menus)

    restaurants_df = pd.DataFrame(restaurant_rows)
    if restaurants_df.empty:
        latest_restaurant_file = CURATED_LATEST_DIR / "Restaurant.csv"
        if latest_restaurant_file.exists():
            restaurants_df = pd.read_csv(latest_restaurant_file)
    deduped_restaurants = deduplicate_restaurants(restaurants_df)

    if deduped_restaurants.empty:
        deduped_restaurants = pd.DataFrame(columns=RESTAURANT_COLUMNS)

    deduped_restaurants["Fetch_Time"] = run_time.isoformat()
    for col in RESTAURANT_COLUMNS:
        if col not in deduped_restaurants.columns:
            deduped_restaurants[col] = ""

    menu_df = pd.DataFrame(menu_rows)
    if not menu_df.empty:
        mapper = deduped_restaurants[["Restaurant_ID", "Source_Record_ID"]].drop_duplicates()
        menu_df = menu_df.merge(mapper, on="Source_Record_ID", how="left")

    historical_medians = load_historical_prices()
    if menu_df.empty:
        menu_df = fallback_menu_from_medians(deduped_restaurants, historical_medians)

    product_seed = load_products()
    products_df = build_products(product_seed, menu_df)
    menu_df["Dish_Name"] = menu_df["Dish_Name"].apply(standardize_dish_name)
    menu_df = menu_df.merge(products_df[["Product_ID", "Dish_Name"]], on="Dish_Name", how="left")

    menu_df["Fetch_Time"] = run_time.isoformat()
    menu_df["Price_Date"] = menu_df.get("Price_Date", run_time.date().isoformat())
    menu_df["Menu_Price_ID"] = [f"M{i+1:06d}" for i in range(len(menu_df))]
    menu_df["Dish_rating"] = menu_df.get("Dish_rating")

    for col, default in {
        "Portion_Size": "Regular",
        "Serving_Unit": "Plate",
        "Menu_Type": "Main Course",
        "Source_URL": "",
        "Source_System": "derived",
    }.items():
        if col not in menu_df.columns:
            menu_df[col] = default
        menu_df[col] = menu_df[col].fillna(default)

    if "Restaurant_ID" not in menu_df.columns:
        menu_df["Restaurant_ID"] = ""

    fact_df = menu_df[
        [
            "Menu_Price_ID",
            "Restaurant_ID",
            "Product_ID",
            "Price",
            "Portion_Size",
            "Serving_Unit",
            "Dish_rating",
            "Menu_Type",
            "Source_URL",
            "Price_Date",
            "Fetch_Time",
            "Source_System",
        ]
    ].copy()

    fact_df = quality_filter_prices(fact_df)
    for col in FACT_COLUMNS:
        if col not in fact_df.columns:
            fact_df[col] = ""

    row_counts = {
        "restaurant": len(deduped_restaurants),
        "product": len(products_df),
        "fact": len(fact_df),
    }
    save_curated(timestamp, deduped_restaurants, products_df, fact_df)
    append_monitoring(timestamp, source_rows, row_counts, errors)

    print(json.dumps({"status": "ok", "timestamp": timestamp, "counts": row_counts}, indent=2))


if __name__ == "__main__":
    run_pipeline()
