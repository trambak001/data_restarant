from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "external" / "experience_submissions.csv"

FIELDS = {
    "Restaurant name": "Restaurant_Name",
    "Area": "Area",
    "Visit date": "Visit_Date",
    "Overall experience": "Experience_Rating",
    "Value for money": "Value_Rating",
    "Dish observed (optional)": "Dish_Name",
    "Dish price in INR (optional)": "Dish_Price",
    "What did you observe?": "Experience_Notes",
    "Public source link (optional)": "Source_URL",
}


def parse_body(body: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for label, key in FIELDS.items():
        match = re.search(rf"### {re.escape(label)}\s*\n\s*(.*?)(?=\n### |\Z)", body, re.S | re.I)
        values[key] = " ".join(match.group(1).strip().split()) if match else ""
    return values


def rating(value: str) -> str:
    match = re.match(r"([1-5])", value)
    return match.group(1) if match else ""


def run() -> None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH is required")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue", {})
    issue_number = str(issue.get("number", ""))
    labels = {label.get("name") for label in issue.get("labels", [])}
    if "market-experience" not in labels:
        return

    values = parse_body(issue.get("body", ""))
    values["Experience_Rating"] = rating(values["Experience_Rating"])
    values["Value_Rating"] = rating(values["Value_Rating"])
    if not values["Restaurant_Name"] or not values["Area"] or not values["Experience_Notes"]:
        raise SystemExit("Required experience fields are missing")

    dish_price = values["Dish_Price"].replace(",", "").replace("₹", "").strip()
    if dish_price and not re.fullmatch(r"\d+(?:\.\d{1,2})?", dish_price):
        raise SystemExit("Dish price must be a number in INR")
    values["Dish_Price"] = dish_price

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, str]] = []
    if OUTPUT.exists():
        with OUTPUT.open(newline="", encoding="utf-8") as file:
            existing = list(csv.DictReader(file))
    if any(row.get("Issue_Number") == issue_number for row in existing):
        return

    row = {
        "Issue_Number": issue_number,
        "Submitted_At": datetime.now(timezone.utc).isoformat(),
        **values,
        "Status": "pending_review",
    }
    with OUTPUT.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=row.keys())
        if not existing:
            writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    run()
