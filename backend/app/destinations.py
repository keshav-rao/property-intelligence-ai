"""Approved official destinations and deep-link builders.

Every link the assistant shows comes from here or from a catalogue record, so it can
never invent a URL. All entries were checked to resolve on 2026-11-19.
"""
from __future__ import annotations

from app.catalog import WASALT_CITY_SLUG

DESTINATIONS: dict[str, dict] = {
    "darglobal_home": {"label": "DarGlobal website", "url": "https://darglobal.co.uk/", "platform": "darglobal"},
    "darglobal_projects": {"label": "All DarGlobal projects", "url": "https://darglobal.co.uk/projects", "platform": "darglobal"},
    "darglobal_contact": {"label": "Contact DarGlobal", "url": "https://darglobal.co.uk/get-in-touch", "platform": "darglobal"},
    "darglobal_investor": {"label": "DarGlobal investor relations", "url": "https://darglobal.co.uk/investor", "platform": "darglobal"},
    "darglobal_why": {"label": "Why invest with DarGlobal", "url": "https://darglobal.co.uk/why-invest", "platform": "darglobal"},
    "darglobal_1of1": {"label": "Premiere Edition collection", "url": "https://darglobal.co.uk/one-of-one", "platform": "darglobal"},
    "wasalt_home": {"label": "Wasalt website", "url": "https://wasalt.sa/en", "platform": "wasalt"},
    "wasalt_auctions": {"label": "Wasalt Auctions", "url": "https://auction.wasalt.sa/en", "platform": "wasalt"},
    "wasalt_daily": {"label": "Wasalt Daily Rentals", "url": "https://wasalt.sa/en/wb-daily-rentals", "platform": "wasalt"},
    "wasalt_business": {"label": "Wasalt Business (Matchmaker)", "url": "https://business.wasalt.sa/en", "platform": "wasalt"},
    "wasalt_post": {"label": "List a property on Wasalt", "url": "https://wasalt.sa/en/post-property", "platform": "wasalt"},
    "wasalt_projects": {"label": "Projects on Wasalt", "url": "https://wasalt.sa/en/sale/search?countryId=1&propertyFor=sale&type=residential&project=true", "platform": "wasalt"},
    "wasalt_about": {"label": "About Wasalt", "url": "https://wasalt.sa/en/corporate", "platform": "wasalt"},
}

DG_COUNTRY = {"United Arab Emirates": "properties-in-uae", "Saudi Arabia": "properties-in-saudi-arabia",
              "Oman": "properties-in-oman", "Qatar": "properties-in-qatar", "Spain": "properties-in-spain",
              "United Kingdom": "properties-in-uk"}
CITY_COUNTRY = {"riyadh": "Saudi Arabia", "jeddah": "Saudi Arabia", "dubai": "United Arab Emirates",
                "ras al khaimah": "United Arab Emirates", "muscat": "Oman", "doha": "Qatar", "simaisma": "Qatar",
                "london": "United Kingdom", "benahavis": "Spain", "casares": "Spain"}


def dest(key: str) -> dict:
    return dict(DESTINATIONS[key], key=key)


def wasalt_search(purpose: str | None, city: str | None, ptype: str | None) -> dict:
    """Live Wasalt category page for these filters (patterns verified on wasalt.sa)."""
    purpose = purpose if purpose in ("sale", "rent") else "sale"
    slug = WASALT_CITY_SLUG.get(city or "")
    if not slug:
        return {"label": "Search all properties on Wasalt", "url": "https://wasalt.sa/en", "platform": "wasalt", "key": "wasalt_search"}
    kind = {"apartment": "apartments", "villa": "villas", "land": "lands"}.get(ptype or "", "properties")
    if kind == "lands" and purpose == "rent":
        kind = "properties"
    city_name = {"khobar": "Al Khobar"}.get(city, city.title())
    noun = {"apartments": "apartments", "villas": "villas", "lands": "land", "properties": "properties"}[kind]
    return {"label": f"Live {noun} for {purpose} in {city_name} on Wasalt",
            "url": f"https://wasalt.sa/en/{kind}-for-{purpose}-in-{slug}", "platform": "wasalt", "key": "wasalt_search"}


def darglobal_country(country: str | None, city: str | None = None) -> dict:
    country = country or CITY_COUNTRY.get(city or "")
    slug = DG_COUNTRY.get(country or "")
    if not slug:
        return dest("darglobal_projects")
    return {"label": f"DarGlobal projects in {country}", "url": f"https://darglobal.co.uk/projects/{slug}",
            "platform": "darglobal", "key": "darglobal_country"}
