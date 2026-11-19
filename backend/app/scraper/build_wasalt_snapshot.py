"""Turn the captured Wasalt category-page rows into data/raw/wasalt/snapshot.json.

How the rows were captured (2026-11-19): Wasalt answers 403 to a self-identified bot
User-Agent, and we do not disguise automated clients as browsers. So the 26 public
category pages (6 cities x sale/rent x apartments/villas, plus land in Riyadh and
Jeddah) were opened in a normal browser session, at a human pace, and up to 12 listings
per page were recorded with an allow-list of listing facts. Owner, broker, phone and
contact fields were never read into the capture.

Row format:
[id, "s"|"r", sub_type, city, district, price, price_period, bedrooms, bathrooms,
 built_up_area_sqm, age, furnishing, first_image_file, slug]

Run:  python -m app.scraper.build_wasalt_snapshot
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAPTURE = ROOT / "data" / "raw" / "wasalt" / "_capture"
OUT = ROOT / "data" / "raw" / "wasalt" / "snapshot.json"
IMG = "https://imagedelivery.net/1DNKFJPRaeUdy_j8F7HT3w/production/properties/{pid}/images/{name}/width=640,quality=70,format=auto"
COLLECTED = "2026-11-19T00:00:00+00:00"


def plausible(sub: str, purpose: str, price, area) -> tuple[float | None, float | None]:
    """Drop values that are clearly data-entry errors on the source listing."""
    try:
        price = float(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        price = None
    try:
        area = float(area) if area not in (None, "") else None
    except (TypeError, ValueError):
        area = None
    if sub == "Apartment" and area and area > 600:  # usually the plot area typed into built-up area
        area = None
    if price is not None:
        if purpose == "sale" and (price < 50_000 or price > 200_000_000):
            price = None
        if purpose == "rent" and price < 6_000:  # likely a daily or monthly figure in the yearly field
            price = None
    return price, area


def run() -> None:
    rows = []
    for f in sorted(CAPTURE.glob("rows_*.json")):
        rows += json.loads(f.read_text(encoding="utf-8"))
    out, seen = [], set()
    for r in rows:
        pid, p, sub, city, district, price, period, beds, baths, area, age, furn, img, slug = r
        if pid in seen or not slug or not sub:
            continue
        seen.add(pid)
        purpose = "sale" if p == "s" else "rent"
        price, area = plausible(sub, purpose, price, area)
        out.append({
            "id": pid,
            "title": None,
            "purpose": purpose,
            "sub_type": sub,
            "city": city,
            "district": district,
            "price": price,
            "price_period": period if purpose == "rent" and price else None,
            "currency": "SAR",
            "bedrooms": beds,
            "bathrooms": baths,
            "area_sqm": area,
            "age": age,
            "furnishing": furn,
            "images": [IMG.format(pid=pid, name=img)] if img else [],
            "url": f"https://wasalt.sa/en/property/{purpose}/{slug}",
            "scraped_at": COLLECTED,
        })
    OUT.write_text(json.dumps({
        "source": "https://wasalt.sa (public category pages)",
        "attribution": "Source: Wasalt.sa",
        "collected_at": COLLECTED,
        "note": "Snapshot for demonstration. Prices and availability change; always confirm on wasalt.sa.",
        "listings": out,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {len(out)} listings to {OUT}")


if __name__ == "__main__":
    run()
