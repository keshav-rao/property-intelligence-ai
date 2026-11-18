"""Data normalization pipeline for DarGlobal and Wasalt scraped data.

Transforms raw heterogeneous records into clean, uniform schema:
- data/processed/properties.json
- data/processed/knowledge_docs.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import get_data_dir

RAW_DIR = get_data_dir() / "raw"
PROCESSED_DIR = get_data_dir() / "processed"


def clean_html(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_wasalt_listing(raw: dict) -> dict | None:
    details = raw.get("details") or {}
    pinfo = details.get("propertyInfo") or {}
    if not pinfo:
        return None

    # Determine ID
    listing_id = f"wasalt-{details.get('id') or pinfo.get('slug')}"
    title = pinfo.get("title") or pinfo.get("propertyName") or "Saudi Real Estate Listing"
    url = raw.get("url") or f"https://wasalt.sa/en/property/{pinfo.get('propertyFor')}/{pinfo.get('slug')}"
    
    # Purpose & Price
    purpose = (pinfo.get("propertyFor") or "sale").lower()
    sale_price = pinfo.get("salePrice")
    rent_price = pinfo.get("expectedRent")
    conversion_price = pinfo.get("conversionPrice")
    
    price_num = 0
    price_display = "Contact for Price"
    currency = pinfo.get("currencyType") or "SAR"
    
    if purpose == "rent" and rent_price:
        try:
            price_num = float(rent_price)
            freq = pinfo.get("expectedRentType") or "/year"
            price_display = f"{int(price_num):,} {currency} {freq}".strip()
        except (ValueError, TypeError):
            price_display = f"{rent_price} {currency}"
    elif conversion_price:
        try:
            price_num = float(conversion_price)
            price_display = f"{int(price_num):,} {currency}"
        except (ValueError, TypeError):
            price_display = f"{conversion_price} {currency}"
    elif sale_price:
        try:
            price_num = float(sale_price)
            price_display = f"{int(price_num):,} {currency}"
        except (ValueError, TypeError):
            price_display = f"{sale_price} {currency}"

    # Extract bedrooms & area from attributes
    bedrooms = None
    area_sqm = None
    bathrooms = None
    for attr in details.get("attributes") or []:
        k = attr.get("key", "").lower()
        v = attr.get("value")
        if "bedroom" in k:
            bedrooms = v
        elif "area" in k or "builtup" in k:
            area_sqm = v
        elif "bathroom" in k:
            bathrooms = v

    city = pinfo.get("city") or "Saudi Arabia"
    district = pinfo.get("district") or pinfo.get("zone") or ""
    prop_type = pinfo.get("propertySubType") or pinfo.get("propertyMainType") or "Residential"

    # Amenities
    amenities = []
    for item in raw.get("amenities") or []:
        if isinstance(item, dict) and item.get("name"):
            amenities.append(item["name"])
        elif isinstance(item, str):
            amenities.append(item)
    for tag in pinfo.get("tags") or []:
        if isinstance(tag, dict) and tag.get("name"):
            amenities.append(tag["name"])

    desc = clean_html(pinfo.get("description") or "")

    return {
        "id": listing_id,
        "platform": "wasalt",
        "name": title,
        "title": f"{title} in {district}, {city}".strip(", "),
        "url": url,
        "country": "Saudi Arabia",
        "city": city,
        "district": district,
        "property_type": prop_type,
        "category": pinfo.get("propertyMainType") or "Residential",
        "purpose": purpose,
        "developer": "Wasalt Marketplace Partner / Licensed Broker",
        "brand_partner": None,
        "status": "Active Listing",
        "price_display": price_display,
        "price_numeric": price_num,
        "currency": currency,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "area_sqm": area_sqm,
        "amenities": list(dict.fromkeys(amenities)),
        "description": desc,
        "investment_highlights": f"Listed on Wasalt real estate marketplace in {city}.",
        "scraped_at": raw.get("scraped_at") or ""
    }


def normalize_all() -> tuple[list[dict], list[dict]]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    all_properties: list[dict] = []
    knowledge_docs: list[dict] = []

    # 1. Load DarGlobal Projects
    dg_proj_file = RAW_DIR / "darglobal" / "projects.json"
    if dg_proj_file.exists():
        with open(dg_proj_file, "r", encoding="utf-8") as f:
            dg_projects = json.load(f)
        for p in dg_projects:
            all_properties.append({
                "id": p["id"],
                "platform": "darglobal",
                "name": p.get("name", p.get("title")),
                "title": p.get("title", p.get("name")),
                "url": p.get("url", ""),
                "country": p.get("country", ""),
                "city": p.get("city", ""),
                "district": p.get("district", ""),
                "property_type": p.get("property_type", "Residential"),
                "category": p.get("category", "Residential"),
                "purpose": p.get("purpose", "sale"),
                "developer": p.get("developer", "Dar Global PLC"),
                "brand_partner": p.get("brand_partner"),
                "status": p.get("status", "Off-plan"),
                "price_display": p.get("price_hint", "Price Upon Request"),
                "price_numeric": p.get("price_numeric", 0),
                "currency": p.get("currency", "SAR"),
                "bedrooms": p.get("bedrooms"),
                "bathrooms": None,
                "area_sqm": p.get("area_hint"),
                "amenities": p.get("amenities", []),
                "description": p.get("description", ""),
                "investment_highlights": p.get("investment_highlights", ""),
                "scraped_at": p.get("scraped_at", "")
            })
        print(f"[Normalize] Processed {len(dg_projects)} DarGlobal projects")

    # 2. Load DarGlobal Company Docs
    dg_comp_file = RAW_DIR / "darglobal" / "company.json"
    if dg_comp_file.exists():
        with open(dg_comp_file, "r", encoding="utf-8") as f:
            dg_company = json.load(f)
        for c in dg_company:
            knowledge_docs.append({
                "id": c.get("id", f"dg-doc-{len(knowledge_docs)}"),
                "platform": "darglobal",
                "title": c.get("title", "DarGlobal Information"),
                "url": c.get("url", "https://darglobal.co.uk"),
                "doc_type": c.get("type", "company_profile"),
                "city": "Global",
                "text": c.get("text", ""),
                "scraped_at": c.get("scraped_at", "")
            })
        print(f"[Normalize] Processed {len(dg_company)} DarGlobal company docs")

    # 3. Load Wasalt Listings
    wasalt_listings_dir = RAW_DIR / "wasalt" / "listings"
    if wasalt_listings_dir.exists():
        listing_files = list(wasalt_listings_dir.glob("*.json"))
        wasalt_count = 0
        for lf in listing_files:
            try:
                with open(lf, "r", encoding="utf-8") as f:
                    raw_item = json.load(f)
                parsed = parse_wasalt_listing(raw_item)
                if parsed:
                    all_properties.append(parsed)
                    wasalt_count += 1
            except Exception as e:
                print(f"[Normalize] Skipping {lf.name}: {e}")
        print(f"[Normalize] Processed {wasalt_count} Wasalt property listings")

    # 4. Load Wasalt Market Guides
    guides_file = RAW_DIR / "wasalt" / "market_guides.json"
    if guides_file.exists():
        with open(guides_file, "r", encoding="utf-8") as f:
            guides = json.load(f)
        for g in guides:
            faqs_text = "\n".join(f"Q: {q.get('q')}\nA: {q.get('a')}" for q in g.get("faqs", []))
            full_guide_text = f"Market Guide for {g.get('city', '').title()} ({g.get('purpose', '').title()}):\n"
            if g.get("total_listings"):
                full_guide_text += f"Total available listings: {g['total_listings']:,}.\n"
            if g.get("text"):
                full_guide_text += f"{g['text']}\n\n"
            if faqs_text:
                full_guide_text += f"Frequently Asked Questions:\n{faqs_text}"

            knowledge_docs.append({
                "id": f"wasalt-guide-{g.get('city')}-{g.get('purpose')}",
                "platform": "wasalt",
                "title": g.get("title") or f"Wasalt Market Guide - {g.get('city','').title()} ({g.get('purpose','').title()})",
                "url": g.get("url", "https://wasalt.sa/en"),
                "doc_type": "market_guide",
                "city": g.get("city", "Saudi Arabia"),
                "text": full_guide_text.strip(),
                "scraped_at": g.get("scraped_at", "")
            })
        print(f"[Normalize] Processed {len(guides)} Wasalt market guides")

    # 5. Load Wasalt Info Pages
    pages_file = RAW_DIR / "wasalt" / "pages.json"
    if pages_file.exists():
        with open(pages_file, "r", encoding="utf-8") as f:
            pages = json.load(f)
        for pg in pages:
            text_body = clean_html(pg.get("html") or pg.get("text") or "")
            knowledge_docs.append({
                "id": f"wasalt-page-{len(knowledge_docs)}",
                "platform": "wasalt",
                "title": pg.get("title") or "Wasalt Real Estate Services",
                "url": pg.get("url", "https://wasalt.sa/en"),
                "doc_type": "company_page",
                "city": "Saudi Arabia",
                "text": text_body[:8000],
                "scraped_at": pg.get("scraped_at", "")
            })
        print(f"[Normalize] Processed {len(pages)} Wasalt informational pages")

    # Save to disk
    props_out = PROCESSED_DIR / "properties.json"
    with open(props_out, "w", encoding="utf-8") as f:
        json.dump(all_properties, f, indent=2, ensure_ascii=False)

    docs_out = PROCESSED_DIR / "knowledge_docs.json"
    with open(docs_out, "w", encoding="utf-8") as f:
        json.dump(knowledge_docs, f, indent=2, ensure_ascii=False)

    print(f"\n[Normalize] COMPLETE: {len(all_properties)} total properties saved to {props_out}")
    print(f"[Normalize] COMPLETE: {len(knowledge_docs)} total knowledge documents saved to {docs_out}")

    return all_properties, knowledge_docs


if __name__ == "__main__":
    normalize_all()
