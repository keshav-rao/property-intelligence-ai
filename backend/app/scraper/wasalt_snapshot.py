"""Polite, one-off snapshot of public Wasalt category pages.

Wasalt's robots.txt allows these category paths (only /search is disallowed) and its
llms.txt allows recommending public listings with attribution ("Source: Wasalt.sa") while
asking for moderate crawl rates. So this collector:

* fetches one page (32 listings) per city / property type / purpose, 2 seconds apart;
* keeps an allow-list of listing facts only: no owner, broker, phone or contact fields;
* records the page it came from and the time, so the UI can say how fresh it is and
  send people to the live Wasalt page for current prices and availability.

Run:  python -m app.scraper.wasalt_snapshot
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = "https://wasalt.sa/en"
IMG = "https://imagedelivery.net/1DNKFJPRaeUdy_j8F7HT3w/production/properties/{pid}/images/{name}/width=640,quality=70,format=auto"
UA = "PropertyIntelligenceAI-demo/1.0 (non-commercial assessment project; respects robots.txt)"
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)

CITIES = ["riyadh", "jeddah", "dammam", "al-khobar", "makkah", "madinah"]
PAGES = [(t, p, c) for c in CITIES for p in ("sale", "rent") for t in ("apartments", "villas")]
PAGES += [("lands", "sale", "riyadh"), ("lands", "sale", "jeddah")]

OUT = Path(__file__).resolve().parents[3] / "data" / "raw" / "wasalt" / "snapshot.json"


def _attr(attrs: list[dict], key: str):
    for a in attrs or []:
        if a.get("key") == key:
            return a.get("value")
    return None


def clean(p: dict, page_url: str, scraped_at: str) -> dict | None:
    info = p.get("propertyInfo") or {}
    slug = info.get("slug")
    purpose = info.get("propertyFor")
    if not slug or purpose not in ("sale", "rent"):
        return None
    price, period = None, None
    if purpose == "sale":
        price = info.get("salePrice") or None
    else:
        rent = info.get("expectedRent")
        if isinstance(rent, dict):
            yearly = (rent.get("yearly") or {}).get("amount")
            monthly = (rent.get("monthly") or {}).get("amount")
            price, period = (yearly, "year") if yearly else ((monthly, "month") if monthly else (None, None))
        elif rent:
            price, period = rent, (info.get("rentFreq") or "year")
    images = ((p.get("propertyFiles") or {}).get("images") or [])[:3]
    attrs = p.get("attributes") or []
    return {
        "id": p.get("id"),
        "title": info.get("title"),
        "purpose": purpose,
        "sub_type": info.get("propertySubType"),
        "city": info.get("city"),
        "district": info.get("district") or info.get("zone"),
        "price": price,
        "price_period": period,
        "currency": info.get("currencyType") or "SAR",
        "bedrooms": _attr(attrs, "noOfBedrooms"),
        "bathrooms": _attr(attrs, "noOfBathrooms"),
        "area_sqm": _attr(attrs, "builtUpArea") or _attr(attrs, "landArea"),
        "age": _attr(attrs, "completionYear"),
        "furnishing": info.get("furnishingType"),
        "is_rega": bool(p.get("isRegaProp")),
        "is_verified": bool(p.get("isVerified")),
        "published_at": p.get("publishedAt"),
        "images": [IMG.format(pid=p.get("id"), name=n) for n in images],
        "url": f"{BASE}/property/{purpose}/{slug}",
        "found_on": page_url,
        "scraped_at": scraped_at,
    }


def run() -> None:
    rows: dict[int, dict] = {}
    report = []
    with httpx.Client(headers={"User-Agent": UA, "Accept-Language": "en"}, timeout=30, follow_redirects=True) as client:
        for kind, purpose, city in PAGES:
            url = f"{BASE}/{kind}-for-{purpose}-in-{city}"
            try:
                r = client.get(url)
                r.raise_for_status()
                m = NEXT_DATA.search(r.text)
                props = json.loads(m.group(1))["props"]["pageProps"]["searchResult"]["properties"] if m else []
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                kept = 0
                for p in props:
                    c = clean(p, url, now)
                    if c and c["id"] not in rows:
                        rows[c["id"]] = c
                        kept += 1
                report.append({"url": url, "status": r.status_code, "listings": len(props), "kept": kept})
                print(f"{r.status_code} {url}  {len(props)} listings, {kept} new")
            except Exception as e:  # keep going; one failed page should not stop the snapshot
                report.append({"url": url, "error": str(e)})
                print("ERR", url, e)
            time.sleep(2.0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "https://wasalt.sa (public category pages)",
        "attribution": "Source: Wasalt.sa",
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Snapshot for demonstration. Prices and availability change; always confirm on wasalt.sa.",
        "pages": report,
        "listings": list(rows.values()),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {len(rows)} listings to {OUT}")


if __name__ == "__main__":
    run()
