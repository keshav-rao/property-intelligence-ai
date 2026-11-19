"""Unified catalogue of DarGlobal projects and Wasalt listings.

Both sources are normalised into one record shape so search, ranking, cards and
comparison work the same way for either platform:

    id, platform, kind, title, brand, city, city_key, country, district,
    property_type, type_label, purpose, bedrooms_min, bedrooms_max, bedrooms_label,
    area_sqm, area_label, price, price_period, currency, price_label,
    completion, status, image, url, description, source, collected_at

Rules that keep the data honest:
* DarGlobal does not publish prices on its project pages, so `price` stays None and
  the label says "Price on request".
* "Unknown" availability is never shown as available; Wasalt items are labelled as a
  dated snapshot with a link to the live listing.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from typing import Any

from app.config import settings

WASALT_IMG = "https://imagedelivery.net/1DNKFJPRaeUdy_j8F7HT3w/production/properties/{pid}/images/{name}/width=640,quality=70,format=auto"

CITY_ALIASES: dict[str, list[str]] = {
    "riyadh": ["riyadh", "al riyadh", "ar riyadh"],
    "jeddah": ["jeddah", "jedda", "jiddah"],
    "dammam": ["dammam", "aldammam", "al dammam"],
    "khobar": ["khobar", "al khobar", "al-khobar", "alkhobar"],
    "makkah": ["makkah", "mecca", "makkah al mukarramah", "makka"],
    "madinah": ["madinah", "medina", "al madinah", "madina", "al madinah al munawwarah"],
    "dubai": ["dubai"],
    "ras al khaimah": ["ras al khaimah", "rak", "al marjan", "marjan island"],
    "muscat": ["muscat", "aida"],
    "doha": ["doha", "qetaifan", "lusail"],
    "simaisma": ["simaisma"],
    "london": ["london", "mayfair", "hyde park", "park lane"],
    "benahavis": ["benahavis", "benahavís", "marbella"],
    "casares": ["casares", "cortesin", "finca cortesin"],
}
CITY_DISPLAY = {
    "riyadh": "Riyadh", "jeddah": "Jeddah", "dammam": "Dammam", "khobar": "Al Khobar", "makkah": "Makkah",
    "madinah": "Madinah", "dubai": "Dubai", "ras al khaimah": "Ras Al Khaimah", "muscat": "Muscat",
    "doha": "Doha", "simaisma": "Simaisma", "london": "London", "benahavis": "Benahavís", "casares": "Casares",
}
SAUDI_CITIES = {"riyadh", "jeddah", "dammam", "khobar", "makkah", "madinah"}
# Wasalt URL slugs per city
WASALT_CITY_SLUG = {"riyadh": "riyadh", "jeddah": "jeddah", "dammam": "dammam", "khobar": "al-khobar",
                    "makkah": "makkah", "madinah": "madinah"}

TYPE_MAP = {
    "apartment": "apartment", "apartments": "apartment", "floor": "apartment", "duplex": "apartment",
    "penthouse": "apartment", "studio": "apartment", "residences": "apartment",
    "villa": "villa", "villas": "villa", "townhouse": "villa", "villa / townhouse": "villa", "mansion": "villa",
    "rest house": "villa", "istiraha": "villa",
    "land": "land", "lands": "land", "plot": "land",
    "building": "building", "hotel rooms": "hotel", "hotel room": "hotel", "master community": "community",
}
TYPE_LABEL = {"apartment": "Apartment", "villa": "Villa", "land": "Land", "building": "Building",
              "hotel": "Hotel residence", "community": "Master community"}


def city_key(text: str | None) -> str | None:
    if not text:
        return None
    t = text.lower().replace("-", " ")
    for key, names in CITY_ALIASES.items():
        if any(n in t for n in names):
            return key
    return None


def norm_type(raw: str | None) -> str:
    if not raw:
        return "apartment"
    r = raw.strip().lower()
    if r in TYPE_MAP:
        return TYPE_MAP[r]
    for k, v in TYPE_MAP.items():
        if k in r:
            return v
    return r


def bedrooms_range(label: str | None) -> tuple[int | None, int | None]:
    if not label:
        return None, None
    nums = [int(n) for n in re.findall(r"\d+", label)]
    if not nums:
        return None, None
    return min(nums), max(nums)


def fmt_money(value: float, currency: str = "SAR") -> str:
    if value >= 1_000_000:
        s = f"{value / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{currency} {s}M"
    return f"{currency} {value:,.0f}"


def _darglobal() -> list[dict]:
    path = settings.data_path / "raw" / "darglobal" / "projects_live.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for i, p in enumerate(doc["projects"]):
        bmin, bmax = bedrooms_range(p.get("bedrooms"))
        slug = re.sub(r"[^a-z0-9]+", "-", p["title"].lower()).strip("-")
        ptype = norm_type(p.get("type"))
        status = p.get("status") or "Off-plan"
        out.append({
            "id": f"dg-{slug}",
            "platform": "darglobal",
            "kind": "project",
            "title": p["title"],
            "brand": p.get("brand"),
            "city": p["city"],
            "city_key": city_key(p["city"]) or city_key(p.get("district")),
            "country": p["country"],
            "district": p.get("district"),
            "property_type": ptype,
            "type_label": TYPE_LABEL.get(ptype, (p.get("type") or "").title()),
            "purpose": "sale",
            "bedrooms_min": bmin,
            "bedrooms_max": bmax,
            "bedrooms_label": p.get("bedrooms"),
            "area_sqm": None,
            "area_label": p.get("area"),
            "price": None,
            "price_period": None,
            "currency": None,
            "price_label": "Price on request",
            "completion": p.get("completion"),
            "status": status,
            "available": not any(w in status.lower() for w in ("sold out",)),
            "image": p.get("image"),
            "url": p["url"],
            "description": p.get("description") or "",
            "source": "darglobal.co.uk",
            "collected_at": doc.get("collected_at"),
            "rank_hint": i,
        })
    return out


def _wasalt() -> list[dict]:
    path = settings.data_path / "raw" / "wasalt" / "snapshot.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for r in doc["listings"]:
        ptype = norm_type(r.get("sub_type"))
        ck = city_key(r.get("city"))
        price, period = r.get("price"), r.get("price_period")
        try:
            price = float(price) if price not in (None, "", 0) else None
        except (TypeError, ValueError):
            price = None
        if price:
            label = fmt_money(price) + (" / year" if period == "year" else " / month" if period == "month" else "")
        else:
            label = "Price on request"
        try:
            area = float(r.get("area_sqm")) if r.get("area_sqm") not in (None, "") else None
        except (TypeError, ValueError):
            area = None
        beds = r.get("bedrooms")
        beds = int(beds) if isinstance(beds, (int, float)) or (isinstance(beds, str) and beds.isdigit()) else None
        district = r.get("district")
        tl = TYPE_LABEL.get(ptype, (r.get("sub_type") or "Property").title())
        size = f", {area:,.0f} sqm" if area else ""
        title = (f"{beds}-Bed {tl}{size}" if beds and ptype in ("apartment", "villa") else f"{tl}{size}") + f" in {district or CITY_DISPLAY.get(ck, r.get('city'))}"
        desc_bits = [f"{TYPE_LABEL.get(ptype, ptype.title())} for {r['purpose']} in {district + ', ' if district else ''}{CITY_DISPLAY.get(ck, r.get('city'))}."]
        if beds:
            desc_bits.append(f"{beds} bedroom{'s' if beds != 1 else ''}.")
        if r.get("bathrooms"):
            desc_bits.append(f"{r['bathrooms']} bathrooms.")
        if area:
            desc_bits.append(f"{area:,.0f} sqm built-up area.")
        if r.get("furnishing"):
            desc_bits.append(f"{r['furnishing']}.")
        if r.get("age"):
            desc_bits.append(f"Age: {r['age']}.")
        if r.get("is_rega"):
            desc_bits.append("REGA-registered listing.")
        out.append({
            "id": f"ws-{r['id']}",
            "platform": "wasalt",
            "kind": "listing",
            "title": title,
            "brand": None,
            "city": CITY_DISPLAY.get(ck, r.get("city")),
            "city_key": ck,
            "country": "Saudi Arabia",
            "district": district,
            "property_type": ptype,
            "type_label": TYPE_LABEL.get(ptype, (r.get("sub_type") or "").title()),
            "purpose": r["purpose"],
            "bedrooms_min": beds,
            "bedrooms_max": beds,
            "bedrooms_label": f"{beds} Bedroom{'s' if beds != 1 else ''}" if beds else None,
            "area_sqm": area,
            "area_label": f"{area:,.0f} sqm" if area else None,
            "price": price,
            "price_period": period,
            "currency": "SAR" if price else None,
            "price_label": label,
            "completion": None,
            "status": "Listed on Wasalt (snapshot)",
            "available": None,  # unknown: a snapshot is not proof of availability
            "image": r["images"][0] if r.get("images") else None,
            "url": r["url"],
            "description": " ".join(desc_bits),
            "source": "Wasalt.sa",
            "collected_at": r.get("scraped_at") or doc.get("collected_at"),
            "published_at": r.get("published_at"),
            "rank_hint": 0,
        })
    return out


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    return _darglobal() + _wasalt()


def aliases(item: dict) -> list[str]:
    """Names people use for a project: 'Les Vagues', 'Tierra Viva', 'Neptune', 'Da Vinci Tower'."""
    t = item["title"].lower().replace("&", "and")
    out = {t, t.split(",")[0].strip()}
    out.add(re.sub(r"\s+(by|interiors by|design inspired by)\s+.*$", "", t.split(",")[0]).strip())
    out.add(re.sub(r",?\s*(interiors by|design inspired by)\s+.*$", "", t).strip())
    if t.startswith("the "):
        out |= {o[4:] for o in list(out) if o.startswith("the ")}
    for key, extra in EXTRA_ALIASES.items():
        if key in t:
            out |= set(extra)
    out |= {unicodedata.normalize("NFKD", o).encode("ascii", "ignore").decode() for o in list(out)}
    return [o for o in out if len(o) >= 3]


EXTRA_ALIASES = {
    "trump international hotel and tower dubai": ["trump tower dubai", "trump dubai"],
    "neptune": ["neptune"], "painite": ["painite"], "d-villas": ["d villas", "dvillas"],
    "albert hall": ["albert hall mansions", "albert hall"], "mulliner": ["mulliner"],
    "trump international simaisma": ["trump simaisma", "simaisma"], "trump international hotel, oman": ["trump hotel oman", "trump hotel muscat"],
    "darglobal mansions": ["fendi mansions", "fendi casa mansions"], "azure oceanfront": ["azure villas", "azure"],
    "great escape 2": ["great escape 2"], "padel living": ["padel living", "padel"],
}


def by_id(item_id: str) -> dict | None:
    return next((x for x in load_catalog() if x["id"] == item_id), None)


def card(item: dict) -> dict:
    """Public card shape sent to the UI."""
    keys = ("id", "platform", "kind", "title", "brand", "city", "country", "district", "property_type",
            "type_label", "purpose", "bedrooms_label", "area_label", "price_label", "price", "price_period",
            "currency", "completion", "status", "image", "url", "source", "collected_at")
    return {k: item.get(k) for k in keys}


def stats() -> dict:
    cat = load_catalog()
    dg = [x for x in cat if x["platform"] == "darglobal"]
    ws = [x for x in cat if x["platform"] == "wasalt"]
    return {
        "darglobal_projects": len(dg),
        "darglobal_countries": sorted({x["country"] for x in dg}),
        "wasalt_listings": len(ws),
        "wasalt_cities": sorted({x["city"] for x in ws if x["city"]}),
        "wasalt_snapshot_at": max((x["collected_at"] or "" for x in ws), default=None),
    }
