"""Rule-based understanding: intent + slots from a user message.

Rules (not the LLM) decide what the user wants and which filters apply. That keeps the
behaviour predictable, fast and testable, and means a flaky free model can never break
search or lead capture. The LLM is used afterwards only to phrase grounded answers.
"""
from __future__ import annotations

import re
import unicodedata

from app.catalog import CITY_ALIASES, aliases, load_catalog

WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "single": 1, "double": 2}

BRANDS = {
    "lamborghini": "Automobili Lamborghini", "pagani": "Pagani", "aston martin": "Aston Martin", "missoni": "Missoni",
    "elie saab": "Elie Saab", "fendi": "Fendi Casa", "mouawad": "Mouawad", "trump": "The Trump Organization",
    "marriott": "Marriott", "w residences": "W Hotels", "w hotels": "W Hotels", "nickelodeon": "Nickelodeon",
}
COUNTRIES = {
    "uae": "United Arab Emirates", "emirates": "United Arab Emirates", "united arab emirates": "United Arab Emirates",
    "saudi": "Saudi Arabia", "ksa": "Saudi Arabia", "saudi arabia": "Saudi Arabia", "oman": "Oman", "qatar": "Qatar",
    "spain": "Spain", "uk": "United Kingdom", "united kingdom": "United Kingdom", "england": "United Kingdom",
}
TYPE_WORDS = [
    (r"\b(apartment|apartments|flat|flats|condo|penthouse|duplex|studio)\b", "apartment"),
    (r"\b(villa|villas|house|houses|townhouse|townhouses|mansion|mansions|home with garden)\b", "villa"),
    (r"\b(land|lands|plot|plots)\b", "land"),
    (r"\b(hotel room|hotel rooms|hotel residence|suite|suites)\b", "hotel"),
]

SERVICES = {
    "auctions": r"\bauction",
    "daily_rentals": r"\b(daily rental|daily rent|short stay|short-term|per night|holiday home)",
    "matchmaker": r"\bmatch ?maker|get matched",
    "list_property": r"\b(list my|post (a |my )?property|sell my|advertise my|rent out my)",
    "support": r"\b(customer (care|service|support)|support|helpline|hotline|complain)",
    "investor": r"\b(investor relations|shares?|stock|lse|annual report|financial results)",
}


def _num(s: str) -> float | None:
    s = s.replace(",", "").strip().lower()
    m = re.match(r"(\d+(?:\.\d+)?)\s*(m|mn|million|k|thousand|b|bn|billion)?\b", s)
    if not m:
        return None
    v = float(m.group(1))
    unit = m.group(2) or ""
    if unit in ("m", "mn", "million"):
        v *= 1_000_000
    elif unit in ("k", "thousand"):
        v *= 1_000
    elif unit in ("b", "bn", "billion"):
        v *= 1_000_000_000
    return v


def parse_budget(text: str) -> tuple[float | None, float | None]:
    t = text.lower().replace("sar", "").replace("riyals", "").replace("riyal", "").replace("sr ", "")
    money = r"(\d[\d,]*(?:\.\d+)?\s*(?:m|mn|million|k|thousand|b|bn|billion)?)\b"
    m = re.search(r"between\s+" + money + r"\s*(?:and|to|-)\s*" + money, t)
    if m:
        return _num(m.group(1)), _num(m.group(2))
    m = re.search(r"(?:under|below|less than|max(?:imum)?|up to|upto|within|budget(?: of| is)?|no more than|around|about|<)\s*" + money, t)
    if m:
        v = _num(m.group(1))
        return None, v
    m = re.search(r"(?:over|above|more than|at least|min(?:imum)?|>)\s*" + money, t)
    if m:
        return _num(m.group(1)), None
    # a bare amount with a unit, e.g. "1.2 million" or "900k"
    m = re.search(r"\b(\d+(?:\.\d+)?\s*(?:m|mn|million|k|thousand))\b", t)
    if m and not re.search(r"\b(sqm|sq m|square)\b", t):
        return None, _num(m.group(1))
    return None, None


def parse_bedrooms(text: str) -> int | None:
    t = text.lower()
    if re.search(r"\bstudio\b", t):
        return 0
    m = re.search(r"\b(\d{1,2})\s*(?:-|\s)?\s*(?:bed|beds|bedroom|bedrooms|br|bhk|room|rooms)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(" + "|".join(WORD_NUM) + r")\s*(?:-|\s)?\s*(?:bed|beds|bedroom|bedrooms|room|rooms)\b", t)
    if m:
        return WORD_NUM[m.group(1)]
    return None


def find_city(text: str) -> str | None:
    t = " " + text.lower().replace("-", " ") + " "
    # "London Stock Exchange" is not a city request
    t = t.replace("london stock exchange", " ")
    for key, names in CITY_ALIASES.items():
        for n in names:
            if re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", t):
                return key
    return None


def find_project(text: str) -> dict | None:
    """Match a DarGlobal project mentioned by name (longest name wins)."""
    t = unicodedata.normalize("NFKD", text.lower().replace("&", "and")).encode("ascii", "ignore").decode()
    best = None
    for x in load_catalog():
        if x["platform"] != "darglobal":
            continue
        for n in aliases(x):
            if n in ("aida",) and "aida" not in t.split():
                continue
            if len(n) >= 3 and re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", t):
                if not best or len(n) > best[0]:
                    best = (len(n), x)
    return best[1] if best else None


def parse(text: str) -> dict:
    t = text.lower().strip()
    slots: dict = {}

    # platform
    if re.search(r"\bdar ?global\b|\bdar al arkan\b", t):
        slots["platform"] = "darglobal"
    if re.search(r"\bwasalt\b", t):
        slots["platform"] = "wasalt" if "platform" not in slots else None

    # purpose
    if re.search(r"\b(daily|per night|short stay)\b", t):
        slots["purpose"] = "rent"
    elif re.search(r"\b(rent|rental|rentals|renting|lease|leasing|tenant|to let)\b", t):
        slots["purpose"] = "rent"
    elif re.search(r"\b(buy|buying|purchase|purchasing|for sale|own|invest|investment|investing|off ?plan)\b", t):
        slots["purpose"] = "sale"

    city = find_city(t)
    if city:
        slots["city"] = city
    for k, v in COUNTRIES.items():
        if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t):
            slots["country"] = v
            break
    for pat, ptype in TYPE_WORDS:
        if re.search(pat, t):
            slots["property_type"] = ptype
            break
    beds = parse_bedrooms(t)
    if beds is not None:
        slots["bedrooms"] = beds
    bmin, bmax = parse_budget(t)
    if bmin:
        slots["budget_min"] = bmin
    if bmax:
        slots["budget_max"] = bmax
    for k, v in BRANDS.items():
        if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t):
            slots["brand"] = v
            break
    if re.search(r"\b(branded|luxury|ultra[- ]luxury|premium|high[- ]end|golden visa|second home|holiday home abroad)\b", t):
        slots["luxury"] = True
    project = find_project(t)
    if project:
        slots["project_id"] = project["id"]
        slots["platform"] = "darglobal"

    # "any" answers clear a slot the bot just asked about
    if re.fullmatch(r"(any|anything|no preference|doesn'?t matter|not sure|skip|any type|any budget|flexible)\.?", t):
        slots["_any"] = True

    # intents
    intent = "question"
    if re.fullmatch(r"(hi|hello|hey|salam|salaam|as?salam(u)? ?alaikum|good (morning|afternoon|evening)|marhaba)[!. ]*", t):
        intent = "greeting"
    elif re.fullmatch(r"(thanks|thank you|thx|great|perfect|awesome|ok(ay)?|cool)[!. ]*", t):
        intent = "thanks"
    elif re.search(r"\b(start over|restart|reset|new search|clear (filters|search))\b", t):
        intent = "reset"
    elif re.search(r"\b(compare|comparison|versus|vs\.?|difference between|which is better)\b", t):
        intent = "compare"
    elif re.search(r"\b(contact me|call me|callback|call back|speak (to|with)|talk (to|with)|agent|advisor|adviser|consultant|"
                   r"register (my )?interest|enquire|enquiry|inquire|inquiry|book a (viewing|visit|call)|schedule a (viewing|visit|call)|"
                   r"get in touch|human)\b", t):
        intent = "lead"
    else:
        for svc, pat in SERVICES.items():
            if re.search(pat, t):
                intent = "service"
                slots["service"] = svc
                break
    if intent == "question":
        search_words = re.search(r"\b(find|show|search|looking for|look for|recommend|suggest|options|listings?|available|"
                                 r"want|need|interested in|buy|rent|purchase|any)\b", t)
        has_filters = any(k in slots for k in ("city", "property_type", "bedrooms", "budget_max", "budget_min", "purpose"))
        n_filters = sum(k in slots for k in ("city", "country", "property_type", "bedrooms", "budget_max", "budget_min", "purpose", "brand"))
        question_words = re.match(r"^(what|which|who|how|why|when|where|is|are|does|do|can|could|should|tell me about)", t)
        if project and not search_words:
            intent = "project_info"
        elif (search_words and has_filters) or (has_filters and len(t.split()) <= 6) or (n_filters >= 2 and not question_words):
            intent = "search"
        elif re.search(r"\b(cheaper|lower budget|more expensive|bigger|larger|smaller|more bedrooms|fewer bedrooms|more options|show more)\b", t):
            intent = "refine"
        elif "_any" in slots:
            intent = "search"
        elif project:
            intent = "project_info"
    return {"intent": intent, "slots": {k: v for k, v in slots.items() if v is not None}}
