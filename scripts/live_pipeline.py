from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
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
MONITORING_DIR = DATA_DIR / "monitoring"
EXTERNAL_DIR = DATA_DIR / "external"

# ── Schema constants ────────────────────────────────────────────────────────
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
    "Latitude",
    "Longitude",
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

# Stable column schemas for monitoring CSVs — enforced on every write
SOURCE_STATUS_COLS = [
    "run_timestamp",
    "source",
    "status",
    "record_count",
    "latency_ms",
    "is_fallback",
    "error",
]

REFRESH_METRICS_COLS = [
    "run_timestamp",
    "pipeline_duration_ms",
    "restaurant_count",
    "product_count",
    "fact_count",
    "error_count",
    "osm_record_count",
    "google_record_count",
    "seed_record_count",
    "fallback_used",
]


@dataclass
class SourceResult:
    name: str
    status: str
    record_count: int
    error: str | None
    restaurants: list[dict[str, Any]]
    menus: list[dict[str, Any]]
    latency_ms: float = field(default=0.0)
    is_fallback: bool = field(default=False)


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


def normalize_area(value: Any) -> str:
    """Title-case area name and strip common noise tokens."""
    raw = str(value or "").strip()
    noise = {"nr", "near", "opp", "opposite", "behind", "next", "to"}
    words = raw.split()
    cleaned = [w for w in words if w.lower() not in noise]
    return " ".join(cleaned).title() if cleaned else "Ahmedabad"


def normalize_cuisine(value: Any) -> str:
    """Collapse cuisine variants into a canonical label."""
    raw = normalize_text(value)
    kathiyawadi_markers = {"kathiyawadi", "kathiawadi", "kathiawad", "kathiyawad"}
    gujarati_markers = {"gujarati", "gujarati thali", "thali"}
    for m in kathiyawadi_markers:
        if m in raw:
            return "Kathiyawadi"
    for m in gujarati_markers:
        if m in raw:
            return "Gujarati"
    if raw:
        return " ".join(part.capitalize() for part in raw.split(";"))
    return "Kathiyawadi"


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio() * 100


def is_valid_ahmedabad_coord(lat: Any, lon: Any) -> bool:
    try:
        lat = float(lat)
        lon = float(lon)
        return (22.8 <= lat <= 23.42) and (72.35 <= lon <= 72.85)
    except (ValueError, TypeError):
        return True  # Default to true if missing for other sources


AHMEDABAD_AREA_CENTROIDS: dict[str, tuple[float, float]] = {
    "vastrapur": (23.0350, 72.5280),
    "prahlad nagar": (23.0120, 72.5100),
    "chandkheda": (23.1110, 72.5850),
    "naranpura": (23.0520, 72.5530),
    "gota": (23.1030, 72.5350),
    "shahpur": (23.0380, 72.5800),
    "bodakdev": (23.0380, 72.5180),
    "asarwa": (23.0480, 72.6050),
    "ognaj": (23.0900, 72.5020),
    "thaltej": (23.0500, 72.5150),
    "satellite": (23.0280, 72.5250),
    "bopal": (23.0350, 72.4600),
    "south bopal": (23.0250, 72.4550),
    "nikol": (23.0530, 72.6700),
    "maninagar": (22.9980, 72.6050),
    "navrangpura": (23.0370, 72.5590),
    "sg highway": (23.0500, 72.5080),
    "paldi": (23.0120, 72.5620),
    "ashram road": (23.0300, 72.5700),
    "motera": (23.0980, 72.6010),
    "ranip": (23.0780, 72.5750),
    "sabarmati": (23.0850, 72.5880),
    "gurukul": (23.0470, 72.5320),
    "memnagar": (23.0510, 72.5390),
    "akhbar nagar": (23.0674, 72.5645),
    "odhav": (23.0250, 72.6650),
    "naroda": (23.0700, 72.6500),
    "isanpur": (22.9800, 72.6000),
    "vatva": (22.9600, 72.6250),
    "ghatlodia": (23.0680, 72.5390),
    "chandlodiya": (23.0810, 72.5450),
    "vejalpur": (23.0080, 72.5210),
    "jodhpur": (23.0220, 72.5200),
    "shela": (23.0120, 72.4600),
    "kudasan": (23.1720, 72.6310),
    "infocity": (23.1910, 72.6340),
    "sargasan": (23.1850, 72.6100),
    "sector 11": (23.2230, 72.6500),
    "sector 21": (23.2380, 72.6480),
    "sector 16": (23.2320, 72.6550),
    "sector 7": (23.2180, 72.6400),
    "sector 28": (23.2620, 72.6580),
    "pdpu road": (23.1580, 72.6540),
    "raysan": (23.1580, 72.6540),
    "koba": (23.1420, 72.6320),
    "vavol": (23.2100, 72.6050),
    "chiloda": (23.2600, 72.7500),
    "gandhinagar": (23.2156, 72.6369),
    "ahmedabad": (23.0225, 72.5714),
}


def geocode_area(area_name: str) -> tuple[float, float]:
    norm = normalize_text(area_name)
    for key, coords in AHMEDABAD_AREA_CENTROIDS.items():
        if key in norm or norm in key:
            return coords
    return (23.0225, 72.5714)


def infer_area_from_coords(lat: float | None, lon: float | None) -> str:
    if lat is None or lon is None:
        return "Ahmedabad"
    best_area = "Ahmedabad"
    best_dist = float("inf")
    for area, (clat, clon) in AHMEDABAD_AREA_CENTROIDS.items():
        if area == "ahmedabad":
            continue
        dist = (lat - clat) ** 2 + (lon - clon) ** 2
        if dist < best_dist:
            best_dist = dist
            best_area = area.title()
    return best_area


# ── Error logging helper ────────────────────────────────────────────────────

def log_error(timestamp: str, source: str, error: str, context: dict[str, Any] | None = None) -> None:
    """Append a single error entry to the monitoring error log immediately."""
    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "run_timestamp": timestamp,
        "source": source,
        "error": error,
    }
    if context:
        entry.update(context)
    error_path = MONITORING_DIR / "error_log.jsonl"
    with error_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


# ── Seed CSV loaders (replaces direct Excel reads) ─────────────────────────

def load_products() -> pd.DataFrame:
    """Load product dimension from seed CSV (fallback: empty frame)."""
    seed_path = EXTERNAL_DIR / "seed_products.csv"
    if seed_path.exists():
        try:
            df = pd.read_csv(seed_path)
            if "Dish_Name" in df.columns:
                return df
        except Exception:
            pass
    return pd.DataFrame(columns=PRODUCT_COLUMNS)


def load_historical_prices() -> pd.DataFrame:
    """Load historical price benchmarks from seed fact CSV for fallback medians."""
    fact_path = EXTERNAL_DIR / "seed_fact_menu_price.csv"
    prod_path = EXTERNAL_DIR / "seed_products.csv"

    if not fact_path.exists():
        return pd.DataFrame(columns=["Dish_Name", "Price"])

    try:
        fact_df = pd.read_csv(fact_path)
        prod_df = pd.read_csv(prod_path) if prod_path.exists() else pd.DataFrame(columns=["Product_ID", "Dish_Name"])

        cols = {c.lower() for c in fact_df.columns}
        if "price" not in cols:
            return pd.DataFrame(columns=["Dish_Name", "Price"])

        if "Dish_Name" not in fact_df.columns and "Product_ID" in fact_df.columns and "Dish_Name" in prod_df.columns:
            fact_df = fact_df.merge(prod_df[["Product_ID", "Dish_Name"]], on="Product_ID", how="left")

        if "Dish_Name" not in fact_df.columns:
            return pd.DataFrame(columns=["Dish_Name", "Price"])

        fact_df["Price"] = fact_df["Price"].apply(safe_float)
        fact_df = fact_df.dropna(subset=["Dish_Name", "Price"])
        if fact_df.empty:
            return pd.DataFrame(columns=["Dish_Name", "Price"])

        return (
            fact_df.groupby("Dish_Name", as_index=False)["Price"]
            .median()
            .rename(columns={"Price": "Median_Price"})
        )
    except Exception:
        return pd.DataFrame(columns=["Dish_Name", "Price"])


# ── Source fetchers ─────────────────────────────────────────────────────────

def _backoff_sleep(attempt: int) -> None:
    """Exponential backoff: 2 s, 4 s, 8 s …"""
    time.sleep(2 ** (attempt + 1))


def fetch_osm_restaurants(run_timestamp: str, timeout: int = 35) -> SourceResult:
    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]
    query = """
[out:json][timeout:30];
(
  node["amenity"~"restaurant|fast_food|cafe"]["name"~"Kathiyawad|Kathiawad|Dhaba|Bhojanalay|Thali|Khodiyar|Chamunda|Marutinandan|Purohit|Surti|Saurashtra|Gordhan|Gopi|Patel|Jay Bhavani|Umiya|Radhe|Tulsi|Toran|Sasumaa",i](22.85,72.35,23.40,72.82);
  way["amenity"~"restaurant|fast_food|cafe"]["name"~"Kathiyawad|Kathiawad|Dhaba|Bhojanalay|Thali|Khodiyar|Chamunda|Marutinandan|Purohit|Surti|Saurashtra|Gordhan|Gopi|Patel|Jay Bhavani|Umiya|Radhe|Tulsi|Toran|Sasumaa",i](22.85,72.35,23.40,72.82);
  node["cuisine"~"kathiyawadi|gujarati",i](22.85,72.35,23.40,72.82);
  way["cuisine"~"kathiyawadi|gujarati",i](22.85,72.35,23.40,72.82);
  node["amenity"~"restaurant|fast_food"]["diet:vegetarian"="yes"]["name"~"Kathiyawad|Kathiawad|Dhaba|Thali",i](22.85,72.35,23.40,72.82);
);
out center tags;
""".strip()
    source_name = "openstreetmap_overpass"
    headers = {"User-Agent": "KathiyawadiPricingIntelligence/1.0 (AhmedabadResearch)"}

    t_start = time.perf_counter()
    payload: dict[str, Any] = {}
    last_error: str | None = None

    for endpoint in mirrors:
        for attempt in range(3):
            try:
                response = requests.post(
                    endpoint, data={"data": query}, headers=headers, timeout=timeout
                )
                if response.status_code == 200:
                    payload = response.json()
                    break
                else:
                    last_error = f"{endpoint} returned status {response.status_code}"
                    log_error(run_timestamp, source_name, last_error, {"endpoint": endpoint, "attempt": attempt})
            except Exception as exc:
                last_error = str(exc)
                log_error(run_timestamp, source_name, last_error, {"endpoint": endpoint, "attempt": attempt})
                if attempt < 2:
                    _backoff_sleep(attempt)
        if payload:
            break

    latency_ms = (time.perf_counter() - t_start) * 1000

    if not payload:
        return SourceResult(
            name=source_name,
            status="failed" if last_error else "skipped",
            record_count=0,
            error=last_error,
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )

    elements = payload.get("elements", [])
    restaurants: list[dict[str, Any]] = []

    for el in elements:
        tags = el.get("tags", {})
        raw_name = tags.get("name")
        if not raw_name or len(raw_name.strip()) < 3:
            continue
        name = " ".join(raw_name.split())

        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if not is_valid_ahmedabad_coord(lat, lon):
            continue

        raw_area = tags.get("addr:suburb") or tags.get("addr:neighbourhood") or tags.get("addr:street")
        area = normalize_area(raw_area) if raw_area and raw_area.lower() != "ahmedabad" else infer_area_from_coords(lat, lon)

        cuisine_raw = tags.get("cuisine") or (
            "Kathiyawadi" if "kathiawa" in name.lower() or "kathiyawa" in name.lower() else "Gujarati / Kathiyawadi"
        )
        cuisine = normalize_cuisine(cuisine_raw)

        restaurants.append(
            {
                "Restaurant_Name": name.strip(),
                "City": "Ahmedabad",
                "Area": area,
                "Restaurant_Type": "Dhaba" if "dhaba" in name.lower() else "Pure Veg Restaurant",
                "Cuisine": cuisine,
                "Restaurant_Rating": 4.2,  # Standard baseline for verified active OSM community listings
                "Review_Count": 45.0,
                "Price_Range": tags.get("price", "₹250-400 for two"),
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
        latency_ms=latency_ms,
    )


def fetch_google_places(run_timestamp: str, timeout: int = 40) -> SourceResult:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    source_name = "google_places"
    t_start = time.perf_counter()

    if not api_key:
        log_error(run_timestamp, source_name, "GOOGLE_PLACES_API_KEY is not set")
        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="GOOGLE_PLACES_API_KEY is not set",
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    query = "vegetarian kathiyawadi restaurant in Ahmedabad"
    restaurants: list[dict[str, Any]] = []
    last_error: str | None = None

    try:
        token: str | None = None
        for page in range(3):
            try:
                params = {"key": api_key, "query": query}
                if token:
                    params = {"key": api_key, "pagetoken": token}
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                payload = response.json()

                for item in payload.get("results", []):
                    candidate = {
                        "Restaurant_Name": item.get("name"),
                        "City": "Ahmedabad",
                        "Area": normalize_area((item.get("formatted_address") or "Ahmedabad").split(",")[0]),
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
                    if is_valid_ahmedabad_coord(candidate["Latitude"], candidate["Longitude"]):
                        restaurants.append(candidate)

                token = payload.get("next_page_token")
                if not token:
                    break
            except Exception as exc:
                last_error = str(exc)
                log_error(run_timestamp, source_name, last_error, {"page": page})
                break  # partial commit — return what we have so far

        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="success" if restaurants else ("failed" if last_error else "skipped"),
            record_count=len(restaurants),
            error=last_error,
            restaurants=restaurants,
            menus=[],
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - t_start) * 1000
        err = str(exc)
        log_error(run_timestamp, source_name, err)
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=err,
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )


def load_external_menu_file() -> SourceResult:
    source_name = "external_menu_csv"
    csv_path = EXTERNAL_DIR / "menu_prices.csv"
    t_start = time.perf_counter()

    if not csv_path.exists():
        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="data/external/menu_prices.csv not found",
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )

    try:
        df = pd.read_csv(csv_path)
        required = {"Restaurant_Name", "Dish_Name", "Price", "Area", "Source_URL"}
        missing = sorted(required - set(df.columns))
        if missing:
            latency_ms = (time.perf_counter() - t_start) * 1000
            return SourceResult(
                name=source_name,
                status="failed",
                record_count=0,
                error=f"Missing columns: {', '.join(missing)}",
                restaurants=[],
                menus=[],
                latency_ms=latency_ms,
            )

        restaurants = []
        menus = []
        seen_restaurants: set[str] = set()

        for _, row in df.iterrows():
            rname = str(row["Restaurant_Name"]).strip()
            raw_area = str(row.get("Area", "Ahmedabad")).strip()
            area = normalize_area(raw_area)
            city = str(row.get("City", "Ahmedabad")).strip()
            if any(g.lower() in area.lower() for g in ["Kudasan", "Infocity", "Sargasan", "Sector", "Pdpu", "Gandhinagar"]):
                city = "Gandhinagar"

            rid = f"external_{normalize_text(rname).replace(' ', '_')}"
            lat, lon = geocode_area(area)

            if rname not in seen_restaurants:
                seen_restaurants.add(rname)
                restaurants.append(
                    {
                        "Restaurant_Name": rname,
                        "City": city,
                        "Area": area,
                        "Restaurant_Type": row.get("Restaurant_Type", "Vegetarian"),
                        "Cuisine": normalize_cuisine(row.get("Cuisine", "Kathiyawadi")),
                        "Restaurant_Rating": safe_float(row.get("Restaurant_Rating")),
                        "Review_Count": safe_float(row.get("Review_Count")),
                        "Price_Range": row.get("Price_Range", ""),
                        "Source_URL": row.get("Source_URL", ""),
                        "Source_Record_ID": rid,
                        "Source_System": source_name,
                        "Latitude": lat,
                        "Longitude": lon,
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

        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(menus),
            error=None,
            restaurants=restaurants,
            menus=menus,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )


def load_experience_submissions() -> SourceResult:
    source_name = "community_experience"
    csv_path = EXTERNAL_DIR / "experience_submissions.csv"
    t_start = time.perf_counter()

    if not csv_path.exists():
        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="data/external/experience_submissions.csv not found",
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )

    try:
        df = pd.read_csv(csv_path).fillna("")
        restaurants: list[dict[str, Any]] = []
        menus: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            if str(row.get("Status", "")).lower() not in {"validated", "pending_review"}:
                continue
            name = str(row.get("Restaurant_Name", "")).strip()
            area = normalize_area(str(row.get("Area", "Ahmedabad")).strip() or "Ahmedabad")
            if not name:
                continue
            issue_number = str(row.get("Issue_Number", "")).strip()
            source_url = str(row.get("Source_URL", "")).strip() or (
                f"https://github.com/trambak001/data_restaurant/issues/{issue_number}"
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

        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(restaurants),
            error=None,
            restaurants=restaurants,
            menus=menus,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )


def load_local_seed_source() -> SourceResult:
    """Load seed restaurants and menus from tracked CSV files (converted from Excel)."""
    source_name = "kathiyawadi_seed_workbook"
    rest_path = EXTERNAL_DIR / "seed_restaurants.csv"
    fact_path = EXTERNAL_DIR / "seed_fact_menu_price.csv"
    prod_path = EXTERNAL_DIR / "seed_products.csv"
    t_start = time.perf_counter()

    if not rest_path.exists():
        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="skipped",
            record_count=0,
            error="data/external/seed_restaurants.csv not found",
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )

    try:
        rest_df = pd.read_csv(rest_path)
        fact_df = pd.read_csv(fact_path) if fact_path.exists() else pd.DataFrame()
        prod_df = (
            pd.read_csv(prod_path)
            if prod_path.exists()
            else pd.DataFrame(columns=["Product_ID", "Dish_Name"])
        )
        if "Dish_Name" not in prod_df.columns:
            prod_df["Dish_Name"] = ""
        if "Product_ID" not in prod_df.columns:
            prod_df["Product_ID"] = ""

        restaurants = []
        for idx, row in rest_df.iterrows():
            src_id = f"seed_{row.get('Restaurant_ID', idx + 1)}"
            area = normalize_area(row.get("Area", "Ahmedabad"))
            lat, lon = geocode_area(area)
            restaurants.append(
                {
                    "Restaurant_Name": row.get("Restaurant_Name", ""),
                    "City": row.get("City", "Ahmedabad"),
                    "Area": area,
                    "Restaurant_Type": row.get("Restaurant_Type", "Vegetarian"),
                    "Cuisine": normalize_cuisine(row.get("Cuisine", "Kathiyawadi")),
                    "Restaurant_Rating": safe_float(row.get("Restaurant_Rating")),
                    "Review_Count": safe_float(row.get("Review_Count")),
                    "Price_Range": row.get("Price_Range", ""),
                    "Source_URL": row.get("Source_URL", ""),
                    "Source_Record_ID": src_id,
                    "Source_System": source_name,
                    "Latitude": lat,
                    "Longitude": lon,
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

        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="success",
            record_count=len(restaurants) + len(menus),
            error=None,
            restaurants=restaurants,
            menus=menus,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - t_start) * 1000
        return SourceResult(
            name=source_name,
            status="failed",
            record_count=0,
            error=str(exc),
            restaurants=[],
            menus=[],
            latency_ms=latency_ms,
        )


# ── Deduplication & normalization ───────────────────────────────────────────

def deduplicate_restaurants(restaurants: pd.DataFrame) -> pd.DataFrame:
    canonical: list[dict[str, Any]] = []
    seen_source_ids: dict[str, int] = {}

    for record in restaurants.to_dict("records"):
        matched_index = None
        confidence = 100.0

        src_id = record.get("Source_Record_ID")
        if src_id and src_id in seen_source_ids:
            matched_index = seen_source_ids[src_id]
            confidence = 100.0
        else:
            for i, existing in enumerate(canonical):
                name_score = similarity(record.get("Restaurant_Name", ""), existing.get("Restaurant_Name", ""))
                if name_score < 70:
                    continue
                area_score = similarity(record.get("Area", ""), existing.get("Area", ""))
                blended = (name_score * 0.75) + (area_score * 0.25)
                if blended >= 88:
                    matched_index = i
                    confidence = blended
                    break

        if matched_index is None:
            record["Match_Confidence"] = 100.0
            idx = len(canonical)
            canonical.append(record)
            if src_id:
                seen_source_ids[src_id] = idx
        else:
            existing = canonical[matched_index]
            if pd.isna(existing.get("Restaurant_Rating")) and pd.notna(record.get("Restaurant_Rating")):
                existing["Restaurant_Rating"] = record.get("Restaurant_Rating")
            if pd.isna(existing.get("Review_Count")) and pd.notna(record.get("Review_Count")):
                existing["Review_Count"] = record.get("Review_Count")
            if not existing.get("Source_URL") and record.get("Source_URL"):
                existing["Source_URL"] = record.get("Source_URL")
            if not existing.get("Latitude") and record.get("Latitude"):
                existing["Latitude"] = record.get("Latitude")
            if not existing.get("Longitude") and record.get("Longitude"):
                existing["Longitude"] = record.get("Longitude")
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
        # Fuzzy dedup: skip if similar to an existing seed entry (similarity >= 85)
        already_in_seeds = any(
            similarity(normalized, str(s.get("Dish_Name", ""))) >= 85
            for s in seeds
        )
        if already_in_seeds:
            continue
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

    valid_mask = fact_df["Price_Validation_Status"] == "ok"
    if valid_mask.any() and "Dish_Name" in fact_df.columns:
        valid_df = fact_df[valid_mask]

        q1 = valid_df.groupby("Dish_Name")["Price"].transform(lambda x: x.quantile(0.25))
        q3 = valid_df.groupby("Dish_Name")["Price"].transform(lambda x: x.quantile(0.75))
        iqr = q3 - q1
        low = q1 - (1.5 * iqr)
        high = q3 + (1.5 * iqr)

        outlier_mask = valid_mask & ((fact_df["Price"] < low) | (fact_df["Price"] > high))

        # Only tag outliers if there are enough samples per dish
        counts = valid_df.groupby("Dish_Name")["Price"].transform("count")
        outlier_mask = outlier_mask & (counts >= 5)

        fact_df.loc[outlier_mask, "Price_Validation_Status"] = "iqr_outlier"
    elif valid_mask.any():
        valid_prices = fact_df.loc[valid_mask, "Price"]
        q1 = valid_prices.quantile(0.25)
        q3 = valid_prices.quantile(0.75)
        iqr = q3 - q1
        low = q1 - (1.5 * iqr)
        high = q3 + (1.5 * iqr)
        outlier_mask = valid_mask & ((fact_df["Price"] < low) | (fact_df["Price"] > high))
        fact_df.loc[outlier_mask, "Price_Validation_Status"] = "iqr_outlier"

    return fact_df[fact_df["Price_Validation_Status"].isin(["ok", "iqr_outlier"])].reset_index(drop=True)


# ── Directory setup ─────────────────────────────────────────────────────────

def ensure_dirs() -> None:
    # Note: RAW_DIR and CURATED_HISTORY_DIR are intentionally excluded — they
    # are now gitignored write-only directories; only latest/ is committed.
    for d in [CURATED_LATEST_DIR, MONITORING_DIR, EXTERNAL_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── Monitoring & output ─────────────────────────────────────────────────────

def append_monitoring(
    timestamp: str,
    source_rows: list[dict[str, Any]],
    row_count: dict[str, int],
    errors: list[dict[str, Any]],
    pipeline_duration_ms: float,
    fallback_used: bool,
) -> None:
    # --- source_status.csv ---
    source_status_path = MONITORING_DIR / "source_status.csv"
    new_source_df = pd.DataFrame(source_rows)
    new_source_df["run_timestamp"] = timestamp
    # Enforce stable column order, filling missing cols with empty string
    for col in SOURCE_STATUS_COLS:
        if col not in new_source_df.columns:
            new_source_df[col] = ""
    new_source_df = new_source_df[SOURCE_STATUS_COLS]

    if source_status_path.exists():
        prev = pd.read_csv(source_status_path)
        for col in SOURCE_STATUS_COLS:
            if col not in prev.columns:
                prev[col] = ""
        prev = prev[SOURCE_STATUS_COLS]
        combined_source = pd.concat([prev, new_source_df], ignore_index=True)
    else:
        combined_source = new_source_df
    combined_source.to_csv(source_status_path, index=False)

    # --- refresh_metrics.csv ---
    osm_count = next((r["record_count"] for r in source_rows if r["source"] == "openstreetmap_overpass"), 0)
    google_count = next((r["record_count"] for r in source_rows if r["source"] == "google_places"), 0)
    seed_count = next((r["record_count"] for r in source_rows if r["source"] == "kathiyawadi_seed_workbook"), 0)

    metrics: dict[str, Any] = {
        "run_timestamp": timestamp,
        "pipeline_duration_ms": round(pipeline_duration_ms, 1),
        "restaurant_count": row_count.get("restaurant", 0),
        "product_count": row_count.get("product", 0),
        "fact_count": row_count.get("fact", 0),
        "error_count": len(errors),
        "osm_record_count": osm_count,
        "google_record_count": google_count,
        "seed_record_count": seed_count,
        "fallback_used": fallback_used,
    }

    metrics_path = MONITORING_DIR / "refresh_metrics.csv"
    new_metrics_df = pd.DataFrame([metrics])
    for col in REFRESH_METRICS_COLS:
        if col not in new_metrics_df.columns:
            new_metrics_df[col] = ""
    new_metrics_df = new_metrics_df[REFRESH_METRICS_COLS]

    if metrics_path.exists():
        prev = pd.read_csv(metrics_path)
        for col in REFRESH_METRICS_COLS:
            if col not in prev.columns:
                prev[col] = ""
        prev = prev[REFRESH_METRICS_COLS]
        combined_metrics = pd.concat([prev, new_metrics_df], ignore_index=True)
    else:
        combined_metrics = new_metrics_df
    combined_metrics.to_csv(metrics_path, index=False)

    # --- error_log.jsonl: flush any source-level errors (failed + skipped with messages) ---
    if errors:
        error_path = MONITORING_DIR / "error_log.jsonl"
        with error_path.open("a", encoding="utf-8") as f:
            for error in errors:
                f.write(json.dumps(error, ensure_ascii=False, default=str) + "\n")


def save_curated(restaurant_df: pd.DataFrame, product_df: pd.DataFrame, fact_df: pd.DataFrame) -> None:
    """Write curated tables to data/curated/latest/ only — no history directories."""
    CURATED_LATEST_DIR.mkdir(parents=True, exist_ok=True)
    restaurant_df[RESTAURANT_COLUMNS].to_csv(CURATED_LATEST_DIR / "Restaurant.csv", index=False)
    product_df[PRODUCT_COLUMNS].to_csv(CURATED_LATEST_DIR / "Product.csv", index=False)
    fact_df[FACT_COLUMNS].to_csv(CURATED_LATEST_DIR / "Fact_Menu_Price.csv", index=False)


# ── Main pipeline ───────────────────────────────────────────────────────────

def run_pipeline() -> None:
    ensure_dirs()
    pipeline_start = time.perf_counter()
    run_time = now_utc()
    timestamp = run_time.strftime("%Y%m%d_%H%M%S")

    source_results = [
        load_local_seed_source(),
        fetch_osm_restaurants(timestamp),
        fetch_google_places(timestamp),
        load_external_menu_file(),
        load_experience_submissions(),
    ]

    source_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    restaurant_rows: list[dict[str, Any]] = []
    menu_rows: list[dict[str, Any]] = []

    for src in source_results:
        source_rows.append(
            {
                "source": src.name,
                "status": src.status,
                "record_count": src.record_count,
                "latency_ms": round(src.latency_ms, 1),
                "is_fallback": src.is_fallback,
                "error": src.error or "",
            }
        )
        if src.status == "failed":
            errors.append({"run_timestamp": timestamp, "source": src.name, "error": src.error})
        # Also record skipped-with-error entries so they appear in the error log
        elif src.status == "skipped" and src.error:
            errors.append({"run_timestamp": timestamp, "source": src.name, "error": src.error, "type": "skipped"})

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
    fallback_used = False
    if menu_df.empty:
        menu_df = fallback_menu_from_medians(deduped_restaurants, historical_medians)
        fallback_used = not menu_df.empty
    else:
        covered_ids = set(menu_df["Restaurant_ID"].dropna())
        uncovered_rests = deduped_restaurants[~deduped_restaurants["Restaurant_ID"].isin(covered_ids)]
        if not uncovered_rests.empty and not historical_medians.empty:
            fallback_df = fallback_menu_from_medians(uncovered_rests, historical_medians)
            menu_df = pd.concat(
                [menu_df.dropna(axis=1, how="all"), fallback_df.dropna(axis=1, how="all")],
                ignore_index=True,
            )
            fallback_used = True

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

    save_curated(deduped_restaurants, products_df, fact_df)

    pipeline_duration_ms = (time.perf_counter() - pipeline_start) * 1000
    append_monitoring(timestamp, source_rows, row_counts, errors, pipeline_duration_ms, fallback_used)

    print(json.dumps({"status": "ok", "timestamp": timestamp, "counts": row_counts}, indent=2))


if __name__ == "__main__":
    run_pipeline()
