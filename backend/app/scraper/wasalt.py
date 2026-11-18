"""Wasalt scraper (https://wasalt.sa).

Access basis: robots.txt allows everything except /search; llms.txt permits
data extraction "only for public listing content" at a moderate crawl rate and
forbids collecting contact details. So this scraper:
  * reads public category pages (not /search) to discover current listings
  * fetches each public listing page
  * DROPS advertiser / owner / contact fields before anything is written to disk
  * keeps the request rate low (one request every 2 s)

Run:  python -m app.scraper.wasalt [--per-category 10]
"""
from __future__ import annotations

import argparse
import json
import re

from bs4 import BeautifulSoup

from .common import RAW_DIR, AccessDenied, PoliteClient, now_iso

BASE = "https://wasalt.sa/en"
CITIES = ["riyadh", "jeddah", "makkah", "madinah", "dammam", "al-khobar"]
PURPOSES = ["sale", "rent"]
INFO_PAGES = [
    f"{BASE}/",
    f"{BASE}/s/wasalt-business",
    f"{BASE}/s/masterplan",
    f"{BASE}/s/terms-of-use",
    f"{BASE}/s/terms-of-advertising",
]
OUT = RAW_DIR / "wasalt"

# Never persisted: people, companies, phone/WhatsApp, lead forms, tracking.
PII_KEYS = {
    "leadContactInfo", "propertyOwner", "contactDetails", "ownerName", "resEmployee",
    "scoringData", "packageData", "classificationData", "regaVerifiedInfo",
}
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def next_data(html: str) -> dict:
    m = NEXT_DATA.search(html)
    if not m:
        raise ValueError("no __NEXT_DATA__ payload")
    return json.loads(m.group(1))["props"]["pageProps"]


def strip_pii(obj):
    if isinstance(obj, dict):
        return {k: strip_pii(v) for k, v in obj.items() if k not in PII_KEYS}
    if isinstance(obj, list):
        return [strip_pii(v) for v in obj]
    return obj


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all(["br", "p", "li", "h1", "h2", "h3", "h4", "tr"]):
        br.append("\n")
    return re.sub(r"\n\s*\n+", "\n", soup.get_text(" ")).strip()


def scrape_category(client: PoliteClient, city: str, purpose: str) -> tuple[dict, list[dict]]:
    url = f"{BASE}/properties-for-{purpose}-in-{city}"
    pp = next_data(client.get(url))
    sr = pp.get("searchResult") or {}
    faqs = []
    schema = pp.get("FAQSchema")
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except ValueError:
            schema = None
    if isinstance(schema, dict):
        for q in schema.get("mainEntity", []):
            faqs.append({"q": q.get("name"), "a": html_to_text((q.get("acceptedAnswer") or {}).get("text"))})
    guide = {
        "url": url,
        "city": city,
        "purpose": purpose,
        "scraped_at": now_iso(),
        "total_listings": sr.get("count"),
        "title": (pp.get("metaData") or {}).get("title") if isinstance(pp.get("metaData"), dict) else None,
        "text": html_to_text(pp.get("para")) if isinstance(pp.get("para"), str) else "",
        "faqs": faqs,
    }
    stubs = []
    for prop in sr.get("properties") or []:
        info = prop.get("propertyInfo") or {}
        if prop.get("id") and info.get("slug"):
            stubs.append({"id": prop["id"], "purpose": info.get("propertyFor") or purpose, "slug": info["slug"]})
    return guide, stubs


def scrape_listing(client: PoliteClient, stub: dict) -> dict:
    url = f"{BASE}/property/{stub['purpose']}/{stub['slug']}"
    pp = next_data(client.get(url))
    details = strip_pii(pp["propertyDetailsV3"])
    info = pp.get("infoDetails") or {}
    return {
        "url": url,
        "scraped_at": now_iso(),
        "details": details,
        "amenities": strip_pii(info.get("amenities") or []),
        "fittings": strip_pii(info.get("fittings") or []),
    }


def scrape_info_page(client: PoliteClient, url: str) -> dict:
    html = client.get(url)
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else url
    desc = soup.find("meta", attrs={"name": "description"})
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()
    text = re.sub(r"\s*\n\s*", "\n", soup.get_text("\n")).strip()
    return {
        "url": url,
        "scraped_at": now_iso(),
        "title": title,
        "description": desc.get("content") if desc else None,
        "text": text,
    }


def run(per_category: int = 10) -> None:
    (OUT / "listings").mkdir(parents=True, exist_ok=True)
    client = PoliteClient(delay=2.0)
    guides, pages, seen, failed = [], [], set(), []
    try:
        for url in INFO_PAGES:
            try:
                pages.append(scrape_info_page(client, url))
                print("page   ", url)
            except (AccessDenied, Exception) as e:  # noqa: BLE001 - keep crawling
                failed.append({"url": url, "error": str(e)})
        for city in CITIES:
            for purpose in PURPOSES:
                try:
                    guide, stubs = scrape_category(client, city, purpose)
                except (AccessDenied, Exception) as e:  # noqa: BLE001
                    failed.append({"url": f"{city}/{purpose}", "error": str(e)})
                    continue
                guides.append(guide)
                print(f"category {city}/{purpose}: {len(stubs)} listings on page")
                taken = 0
                for stub in stubs:
                    if taken >= per_category:
                        break
                    if stub["id"] in seen:
                        continue
                    try:
                        rec = scrape_listing(client, stub)
                    except (AccessDenied, Exception) as e:  # noqa: BLE001
                        failed.append({"url": stub["slug"], "error": str(e)})
                        continue
                    seen.add(stub["id"])
                    taken += 1
                    (OUT / "listings" / f"{stub['id']}.json").write_text(
                        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"
                    )
    finally:
        client.close()
    (OUT / "market_guides.json").write_text(json.dumps(guides, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "scrape_report.json").write_text(
        json.dumps(
            {"finished_at": now_iso(), "listings": len(seen), "market_guides": len(guides),
             "pages": len(pages), "failed": failed},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    print(f"done: {len(seen)} listings, {len(guides)} guides, {len(pages)} pages, {len(failed)} failed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=10)
    run(ap.parse_args().per_category)
