"""Conversation engine: state, guided workflow, recommendations and grounded answers.

One turn:
1. Understand the message (rules in nlu.py) and merge new preferences into the session.
2. Decide the next step: answer a question, ask for one missing detail, recommend,
   compare, open the enquiry form or send the user to the right official page.
3. Build a structured reply (cards, sources, link buttons, quick replies) and, where it
   helps, let the LLM write the wording from verified context only.

The structured parts never depend on the LLM. If the model is slow or down, the
deterministic text is used and everything else still works.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field

from app import rag
from app.catalog import CITY_DISPLAY, SAUDI_CITIES, aliases, by_id, card, fmt_money, load_catalog
from app.config import settings
from app.destinations import darglobal_country, dest, wasalt_search
from app.nlu import parse

FILTER_KEYS = ("platform", "purpose", "city", "country", "property_type", "bedrooms", "budget_min", "budget_max", "brand", "luxury")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{7,}\d)(?!\d)")

SAUDI_CITY_REPLIES = ["Riyadh", "Jeddah", "Dammam", "Al Khobar", "Makkah", "Madinah"]
DG_DEST_REPLIES = ["Saudi Arabia", "Dubai (UAE)", "Oman (AIDA)", "Qatar", "Spain", "London", "Show all projects"]
HOME_REPLIES = ["Buy a home in Saudi Arabia", "Rent in Riyadh", "DarGlobal branded residences",
                "Compare two projects", "Wasalt auctions", "Talk to an advisor"]


@dataclass
class Session:
    id: str
    filters: dict = field(default_factory=dict)
    asked: set = field(default_factory=set)
    awaiting: str | None = None
    last_results: list = field(default_factory=list)
    last_project: str | None = None
    history: list = field(default_factory=list)
    updated: float = field(default_factory=time.time)


_sessions: dict[str, Session] = {}


def get_session(sid: str | None) -> Session:
    now = time.time()
    for k in [k for k, s in _sessions.items() if now - s.updated > settings.session_ttl_minutes * 60]:
        _sessions.pop(k, None)
    if sid and sid in _sessions:
        s = _sessions[sid]
    else:
        s = Session(id=sid or uuid.uuid4().hex)
        _sessions[s.id] = s
    s.updated = now
    return s


def redact(text: str) -> str:
    """Strip contact details before anything is sent to the LLM provider."""
    return PHONE.sub("[phone removed]", EMAIL.sub("[email removed]", text))


# ----------------------------------------------------------------------------- state


def merge(s: Session, slots: dict, intent: str) -> list[str]:
    """Merge new slots; return the names of filters that changed."""
    changed = []
    if intent == "reset":
        s.filters, s.asked, s.awaiting, s.last_results = {}, set(), None, []
        return ["reset"]
    search_slots = [k for k in ("purpose", "city", "country", "property_type", "bedrooms", "budget_max", "brand", "luxury") if k in slots]
    if intent == "search" and len(search_slots) >= 2 and any(k in slots for k in ("purpose", "city", "country", "brand"))             and any(s.filters.get(k) not in (None, "any") for k in FILTER_KEYS):
        # a new, fully-stated request starts a fresh search instead of piling onto the old one
        s.filters, s.asked, s.awaiting = {}, set(), None
        changed.append("new_search")
    if slots.get("_any") and s.awaiting:
        s.filters[s.awaiting] = "any"
        changed.append(s.awaiting)
    for k in FILTER_KEYS:
        if k in slots and s.filters.get(k) != slots[k]:
            s.filters[k] = slots[k]
            changed.append(k)
    f = s.filters
    # keep geography consistent: a new country drops a city elsewhere, a new city drops a mismatched country
    from app.destinations import CITY_COUNTRY
    if "country" in changed and f.get("city") and CITY_COUNTRY.get(f["city"], "Saudi Arabia") != f.get("country"):
        if "city" not in slots:
            f.pop("city", None)
    if "city" in changed and f.get("country") and CITY_COUNTRY.get(f["city"], "Saudi Arabia") != f["country"]:
        if "country" not in slots:
            f.pop("country", None)
    # A new city outside Saudi Arabia or a brand implies DarGlobal; a Saudi rental implies Wasalt.
    if "city" in changed and f.get("city") not in SAUDI_CITIES and f.get("city"):
        f["platform"] = "darglobal"
    if "country" in changed and f.get("country") not in (None, "Saudi Arabia"):
        f["platform"] = "darglobal"
    if "brand" in changed:
        f["platform"] = "darglobal"
    if slots.get("platform") == "wasalt" or (f.get("platform") == "wasalt" and "platform" in changed):
        for k in ("brand", "luxury"):
            f.pop(k, None)
        if f.get("country") not in (None, "Saudi Arabia"):
            f.pop("country", None)
        if f.get("city") and f["city"] not in SAUDI_CITIES:
            f.pop("city", None)
    if f.get("platform") == "darglobal" and f.get("purpose") == "rent":
        f["purpose"] = "sale"  # DarGlobal sells; rentals live on Wasalt
    if f.get("purpose") == "rent" and f.get("city") in SAUDI_CITIES and "platform" not in slots and f.get("platform") != "wasalt":
        f["platform"] = "wasalt"
    return changed


def platform_for(f: dict) -> str | None:
    if f.get("platform") in ("darglobal", "wasalt"):
        return f["platform"]
    if f.get("brand") or f.get("luxury"):
        return "darglobal"
    if f.get("purpose") == "rent":
        return "wasalt"
    if f.get("city") in SAUDI_CITIES or f.get("budget_max") or f.get("bedrooms") is not None:
        return "wasalt"
    return None


# ----------------------------------------------------------------------------- search


def match(f: dict, platform: str, relax: int = 0) -> list[dict]:
    """Filter + rank catalogue items. relax=1 widens bedrooms/budget, relax=2 drops type too."""
    out = []
    for x in load_catalog():
        if x["platform"] != platform:
            continue
        if platform == "wasalt" and f.get("purpose") not in (None, "any") and x["purpose"] != f["purpose"]:
            continue
        city = f.get("city")
        if city and city != "any" and x["city_key"] != city:
            continue
        if f.get("country") and f["country"] != "any" and x["country"] != f["country"]:
            continue
        pt = f.get("property_type")
        if pt and pt != "any" and relax < 2 and x["property_type"] != pt:
            continue
        if f.get("brand") and (x.get("brand") or "") != f["brand"]:
            continue
        beds = f.get("bedrooms")
        if beds not in (None, "any") and x["property_type"] != "land":
            lo, hi = x.get("bedrooms_min"), x.get("bedrooms_max")
            if lo is not None:
                slack = 1 if relax else 0
                if not (lo - slack <= beds <= (hi if hi is not None else lo) + slack):
                    continue
            elif platform == "wasalt":
                continue
        bmax, bmin = f.get("budget_max"), f.get("budget_min")
        if platform == "wasalt" and (bmax not in (None, "any") or bmin):
            if x["price"] is None:
                continue
            if bmax not in (None, "any") and x["price"] > bmax * (1.15 if relax else 1.0):
                continue
            if bmin and x["price"] < bmin:
                continue
        out.append(x)

    def score(x):
        s = 0.0
        if x.get("available") is False:
            s -= 5  # sold-out projects go last
        if x.get("image"):
            s += 0.5
        if platform == "wasalt":
            if x["price"] is not None:
                s += 1
                if f.get("budget_max") not in (None, "any"):
                    s += 1 - abs(f["budget_max"] * 0.85 - x["price"]) / max(f["budget_max"], 1)  # close to (just under) budget
            if f.get("bedrooms") not in (None, "any") and x.get("bedrooms_min") == f.get("bedrooms"):
                s += 1
            pub = (x.get("published_at") or "")[:10].replace("-", "")
            if pub.isdigit():
                s += int(pub) * 1e-9  # newer listings first among equals
        else:
            if f.get("luxury") and x.get("brand"):
                s += 1
            s -= 0.01 * x.get("rank_hint", 0)
        return s

    return sorted(out, key=score, reverse=True)


def recommend(f: dict, platform: str) -> tuple[list[dict], str | None]:
    """Return (items, relax_note)."""
    items = match(f, platform)
    if items:
        return items, None
    items = match(f, platform, relax=1)
    if items:
        return items, "No exact matches, so I widened bedrooms by one and the budget by 15%."
    items = match(f, platform, relax=2)
    if items:
        return items, "No exact matches, so I widened bedrooms, budget and property type."
    return [], None


# ----------------------------------------------------------------------------- prompts

SYSTEM = (
    "You are the Property Concierge for DarGlobal (an international luxury developer) and Wasalt (a Saudi property "
    "marketplace). Write warm, concise, professional replies in English.\n"
    "Rules:\n"
    "- Use ONLY the facts in CONTEXT. Never invent prices, availability, payment plans, returns, dates or amenities, "
    "and don't add descriptive adjectives (bright, spacious, stunning) that CONTEXT doesn't state.\n"
    "- Keep brand wording exact: 'interiors by' and 'design inspired by' are not 'designed by'.\n"
    "{platform_rules}"
    "- If CONTEXT does not answer the question, say so plainly and suggest the official page.\n"
    "- Property cards and link buttons are shown under your reply: do not paste URLs, do not repeat every card, "
    "no tables. Mention at most two highlights.\n"
    "- Keep it under {limit} words. Use **bold** only for a key name or number."
)


def ctx_from_items(items: list[dict]) -> str:
    lines = []
    for x in items:
        bits = [x["title"], f"platform: {x['platform']}", f"{x['type_label']} for {x['purpose']}",
                f"location: {', '.join(b for b in [x.get('district'), x['city'], x['country']] if b)}",
                f"price: {x['price_label']}"]
        for k, label in (("bedrooms_label", "bedrooms"), ("area_label", "size"), ("brand", "brand"),
                         ("completion", "completion"), ("status", "status")):
            if x.get(k):
                bits.append(f"{label}: {x[k]}")
        lines.append("- " + "; ".join(bits))
    return "\n".join(lines)


def ctx_from_docs(docs: list[dict]) -> str:
    return "\n\n".join(f"[{d['title']}]\n{d['text']}" for d in docs)


def llm_messages(s: Session, user_text: str, context: str, task: str, limit: int = 90) -> list[dict]:
    ctx = context.lower()
    rules = ""
    if "platform: darglobal" in ctx or "darglobal" in ctx:
        rules += ("- DarGlobal items: prices are not published; say they are on request from DarGlobal's sales team "
                  "(register interest on the project page). Never send DarGlobal buyers to Wasalt.\n")
    if "platform: wasalt" in ctx or "wasalt" in ctx:
        rules += "- Wasalt items are a dated snapshot: prices and availability can change, so suggest confirming on Wasalt.\n"
    msgs = [{"role": "system", "content": SYSTEM.format(limit=limit, platform_rules=rules)}]
    for h in s.history[-4:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": f"CONTEXT:\n{context}\n\nTASK: {task}\n\nUSER MESSAGE: {redact(user_text)}"})
    return msgs


# ----------------------------------------------------------------------------- replies


def describe_filters(f: dict) -> str:
    parts = []
    if f.get("bedrooms") not in (None, "any"):
        parts.append("studio" if f["bedrooms"] == 0 else f"{f['bedrooms']}-bedroom")
    pt = f.get("property_type")
    parts.append({"apartment": "apartments", "villa": "villas", "land": "plots", "hotel": "hotel residences"}.get(pt, "properties") if pt != "any" else "properties")
    if f.get("purpose") in ("sale", "rent"):
        parts.append("for rent" if f["purpose"] == "rent" else "for sale")
    if f.get("city") not in (None, "any"):
        parts.append("in " + CITY_DISPLAY.get(f["city"], f["city"].title()))
    elif f.get("country") not in (None, "any"):
        parts.append("in " + f["country"])
    if f.get("budget_max") not in (None, "any"):
        parts.append("up to " + fmt_money(f["budget_max"]))
    if f.get("brand"):
        parts.append(f"by {f['brand']}")
    return " ".join(parts)


def base_reply(s: Session) -> dict:
    return {"session_id": s.id, "message_id": uuid.uuid4().hex[:12], "answer": "", "intent": {}, "filters": public_filters(s),
            "recommendations": [], "total_matches": 0, "sources": [], "actions": [], "suggested_replies": [],
            "ui": None, "llm": None}


def public_filters(s: Session) -> dict:
    return {k: v for k, v in s.filters.items() if v not in (None, "any")}


def next_question(s: Session, platform: str) -> tuple[str, list[str], str] | None:
    """Return (question, quick replies, slot) for the most useful missing detail, or None."""
    f = s.filters
    if platform == "wasalt":
        if not f.get("purpose"):
            return "Are you looking to **buy** or **rent**?", ["Buy", "Rent"], "purpose"
        if not f.get("city"):
            return "Which city should I search in?", SAUDI_CITY_REPLIES, "city"
        if not f.get("property_type") and "property_type" not in s.asked:
            opts = ["Apartment", "Villa", "Land", "Any type"] if f["purpose"] == "sale" else ["Apartment", "Villa", "Any type"]
            return "What type of property?", opts, "property_type"
        if f.get("bedrooms") is None and "bedrooms" not in s.asked and f.get("property_type") in ("apartment", "villa"):
            opts = (["3 bedrooms", "4 bedrooms", "5 bedrooms", "6+ bedrooms", "Any"] if f.get("property_type") == "villa"
                    else ["1 bedroom", "2 bedrooms", "3 bedrooms", "4+ bedrooms", "Any"])
            return "How many bedrooms?", opts, "bedrooms"
        if f.get("budget_max") is None and "budget_max" not in s.asked:
            opts = (["Up to SAR 50k / year", "Up to SAR 100k / year", "Up to SAR 200k / year", "Any budget"] if f["purpose"] == "rent"
                    else ["Up to SAR 800k", "Up to SAR 1.2M", "Up to SAR 2.5M", "Any budget"])
            return "What's your budget?", opts, "budget_max"
    else:
        if not any(f.get(k) not in (None,) for k in ("city", "country", "brand")) and "country" not in s.asked:
            return "Where would you like to own? DarGlobal builds in six countries.", DG_DEST_REPLIES, "country"
    return None


def apply_reply_shortcuts(text: str, s: Session) -> str:
    """Map quick-reply wording the rules may not catch onto filter words."""
    t = text.strip().lower()
    m = {"buy": "buy", "rent": "rent", "any type": "any", "any budget": "any", "any": "any",
         "4+ bedrooms": "4 bedrooms", "6+ bedrooms": "6 bedrooms", "show all projects": "any", "dubai (uae)": "dubai", "oman (aida)": "oman"}
    if t in m:
        return m[t]
    m2 = re.match(r"up to sar ([\d.]+\s*[mk]?)", t)
    if m2:
        return f"under {m2.group(1)}"
    return text


def search_turn(s: Session, text: str, reply: dict) -> tuple[dict, list[dict] | None]:
    """Fill the reply for a search; return (reply, llm_messages or None)."""
    f = s.filters
    platform = platform_for(f)
    if not platform:
        reply["answer"] = ("Happy to help you find a property. Are you looking at **Saudi homes on Wasalt** (to buy or rent), "
                           "or **DarGlobal's luxury and branded residences** in Saudi Arabia and abroad?")
        reply["suggested_replies"] = ["Buy a home in Saudi Arabia", "Rent in Saudi Arabia", "DarGlobal branded residences"]
        s.awaiting = "platform"
        return reply, None
    f["platform"] = platform
    q = next_question(s, platform)
    if q:
        question, opts, slot = q
        s.asked.add(slot)
        s.awaiting = slot
        known = describe_filters(f)
        lead_in = f"Great, {known}. " if any(f.get(k) for k in ("purpose", "city", "country", "property_type")) else ""
        reply["answer"] = lead_in + question
        reply["suggested_replies"] = opts
        reply["intent"] = {"name": "search", "platform": platform, "step": f"ask_{slot}"}
        return reply, None
    s.awaiting = None
    s.last_project = None  # an enquiry after a search is about the search, not an older project
    items, note = recommend(f, platform)
    reply["intent"] = {"name": "search", "platform": platform, "step": "results"}
    reply["total_matches"] = len(items)
    top = items[:6]
    s.last_results = [x["id"] for x in top]
    reply["recommendations"] = [card(x) for x in top]
    # Navigation: the live, filtered page on the official site
    if platform == "wasalt":
        reply["actions"].append(wasalt_search(f.get("purpose"), f.get("city"), f.get("property_type")))
        reply["sources"].append({"title": "Wasalt.sa public listings (snapshot 19 Nov 2026)", "url": "https://wasalt.sa/en", "platform": "wasalt"})
        # Cross-platform: DarGlobal projects in the same Saudi city for buyers
        if f.get("purpose") == "sale" and f.get("city") in ("riyadh", "jeddah"):
            dg = [x for x in load_catalog() if x["platform"] == "darglobal" and x["city_key"] == f["city"]]
            if dg:
                reply["also"] = {"title": f"DarGlobal branded projects in {CITY_DISPLAY[f['city']]}", "items": [card(x) for x in dg[:3]]}
    else:
        reply["actions"].append(darglobal_country(f.get("country") if f.get("country") != "any" else None, f.get("city")))
        reply["actions"].append(dest("darglobal_contact"))
        reply["sources"].append({"title": "DarGlobal project pages", "url": "https://darglobal.co.uk/projects", "platform": "darglobal"})
    desc = describe_filters(f)
    if not items:
        reply["answer"] = (f"I couldn't find {desc} in my data. You can see the full, up-to-date range on the official site, "
                           "or change a filter.")
        reply["suggested_replies"] = ["Increase my budget", "Any type", "Try another city", "Start over"]
        return reply, None
    fallback = f"Here {'is' if len(items) == 1 else 'are'} **{len(items)}** match{'' if len(items) == 1 else 'es'} for {desc}."
    if note:
        fallback += " " + note
    if platform == "wasalt":
        fallback += " Prices and availability come from a Wasalt snapshot, so please confirm on the live listing."
    else:
        fallback += " DarGlobal shares prices on request; you can register interest on any project."
    reply["answer"] = fallback
    reply["suggested_replies"] = (["Show villas instead", "Lower my budget", "Compare the top two", "Talk to an advisor"]
                                  if platform == "wasalt" else ["Compare the top two", "Tell me about the first one", "Other countries", "Register interest"])
    if f.get("property_type") == "villa" and platform == "wasalt":
        reply["suggested_replies"][0] = "Show apartments instead"
    task = (f"The user is searching for {desc}. {len(items)} catalogue items match; the top ones are in CONTEXT"
            + (f" ({note})" if note else "") + ". Write a short, friendly intro to these results: say how many matched, "
            "point out one or two standout options by name with a concrete fact each, and give one practical next step.")
    return reply, llm_messages(s, text, ctx_from_items(top), task, limit=70)


def project_turn(s: Session, text: str, reply: dict, project: dict) -> tuple[dict, list[dict]]:
    s.last_project = project["id"]
    s.filters["platform"] = "darglobal"
    reply["intent"] = {"name": "project_info", "platform": "darglobal", "project": project["id"]}
    reply["recommendations"] = [card(project)]
    docs = rag.search(text + " " + project["title"], platform="darglobal", k=4)
    reply["sources"] = [{"title": project["title"], "url": project["url"], "platform": "darglobal"}]
    reply["sources"] += [{"title": d["title"], "url": d["url"], "platform": d["platform"]} for d in docs
                         if d["kind"] == "knowledge"][:2]
    reply["actions"] = [{"label": f"Open {project['title'].split(',')[0]} on DarGlobal", "url": project["url"], "platform": "darglobal", "key": "project"},
                        dest("darglobal_contact")]
    reply["suggested_replies"] = ["Register interest", "Compare with another project", "Similar projects", "Payment plans?"]
    facts = ctx_from_items([project]) + "\nOfficial description: " + project["description"]
    extra = ctx_from_docs([d for d in docs if d["kind"] == "knowledge"][:2])
    reply["answer"] = f"**{project['title']}** — {project['description']}"
    task = ("Answer the user's message about this DarGlobal project using CONTEXT. If they ask about something not in "
            "CONTEXT (price, payment plan, availability), say DarGlobal shares it on request and suggest registering interest.")
    return reply, llm_messages(s, text, facts + "\n\n" + extra, task, limit=110)


def compare_turn(s: Session, text: str, reply: dict, ids: list[str]) -> tuple[dict, list[dict] | None]:
    items = [x for x in (by_id(i) for i in ids) if x][:3]
    if len(items) < 2:
        # find projects named in the message ("compare DG1 and Les Vagues")
        named = []
        for x in load_catalog():
            if x["platform"] != "darglobal":
                continue
            low_text = text.lower().replace("&", "and")
            if any(re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", low_text) for n in aliases(x)):
                named.append(x)
        items = (items + [x for x in named if x not in items])[:3]
    if len(items) < 2 and len(s.last_results) >= 2 and re.search(r"\b(top|first|these|them|both|two)\b", text.lower()):
        items = [by_id(i) for i in s.last_results[:2]]
    reply["intent"] = {"name": "compare"}
    if len(items) < 2:
        reply["answer"] = ("Which two should I compare? Tap **Compare** on two property cards, or name two DarGlobal projects, "
                           "for example *Compare DG1 and Les Vagues*.")
        reply["suggested_replies"] = ["Compare DG1 and Les Vagues", "Compare Trump Tower Jeddah and Neptune", "Show DarGlobal projects in Dubai"]
        return reply, None
    rows = [("Platform", lambda x: "DarGlobal" if x["platform"] == "darglobal" else "Wasalt"),
            ("Location", lambda x: ", ".join(b for b in [x.get("district"), x["city"], x["country"]] if b)),
            ("Type", lambda x: x["type_label"]), ("Bedrooms", lambda x: x.get("bedrooms_label") or "—"),
            ("Size", lambda x: x.get("area_label") or "—"), ("Price", lambda x: x["price_label"]),
            ("Brand partner", lambda x: x.get("brand") or "—"), ("Completion", lambda x: x.get("completion") or "—"),
            ("Status", lambda x: x.get("status") or "—")]
    reply["ui"] = {"type": "compare", "columns": [card(x) for x in items],
                   "rows": [r for r in ({"label": lbl, "values": [fn(x) for x in items]} for lbl, fn in rows)
                            if any(v != "—" for v in r["values"])]}
    reply["recommendations"] = []
    reply["sources"] = [{"title": x["title"], "url": x["url"], "platform": x["platform"]} for x in items]
    reply["answer"] = "Here's a side-by-side comparison of " + " and ".join(f"**{x['title'].split(',')[0]}**" for x in items) + "."
    reply["suggested_replies"] = ["Register interest", "Show similar options", "Start over"]
    task = ("Compare these options for the user in 3-4 short sentences: key differences (location, type, size, brand, "
            "timing) and who each suits. Only use CONTEXT.")
    return reply, llm_messages(s, text, ctx_from_items(items), task, limit=110)


SERVICE_INFO = {
    "auctions": ("wasalt", "kb-wasalt-auctions", ["wasalt_auctions"]),
    "daily_rentals": ("wasalt", "kb-wasalt-daily", ["wasalt_daily"]),
    "matchmaker": ("wasalt", "kb-wasalt-matchmaker", ["wasalt_business"]),
    "list_property": ("wasalt", "kb-wasalt-overview", ["wasalt_post", "wasalt_business"]),
    "support": ("wasalt", "kb-wasalt-overview", ["wasalt_home", "darglobal_contact"]),
    "investor": ("darglobal", "kb-darglobal-overview", ["darglobal_investor"]),
}


def service_turn(s: Session, text: str, reply: dict, svc: str) -> tuple[dict, list[dict]]:
    from app.knowledge import KNOWLEDGE

    platform, kb_id, dest_keys = SERVICE_INFO[svc]
    kb = next(k for k in KNOWLEDGE if k["id"] == kb_id)
    reply["intent"] = {"name": "service", "service": svc, "platform": platform}
    reply["actions"] = [dest(k) for k in dest_keys]
    reply["sources"] = [{"title": kb["title"], "url": kb["url"], "platform": platform}]
    reply["answer"] = kb["text"]
    if svc == "support":
        reply["answer"] = ("For Wasalt, customer care is on **8001233227** or through the Wasalt website and app. "
                           "For DarGlobal, use the Get in touch page, or I can pass your details to an advisor here.")
    reply["suggested_replies"] = ["Talk to an advisor", "Search properties", "What else can you do?"]
    task = "Answer the user's question about this service in 2-3 sentences using only CONTEXT, then point to the button below."
    return reply, llm_messages(s, text, f"[{kb['title']}]\n{kb['text']}", task, limit=80)


def lead_turn(s: Session, reply: dict) -> dict:
    f = s.filters
    project = by_id(s.last_project) if s.last_project else None
    platform = "darglobal" if project else (platform_for(f) or "darglobal")
    interest = project["title"] if project else (describe_filters(f) if f else "")
    reply["intent"] = {"name": "lead", "platform": platform}
    reply["answer"] = ("I can pass your details to an advisor. Share how they should reach you below; nothing is sent until "
                       "you tick the consent box. You can also register directly on the official site.")
    reply["ui"] = {"type": "lead_form", "platform": platform, "interest": interest,
                   "project_id": project["id"] if project else None}
    if project:
        reply["actions"] = [{"label": "Register interest on DarGlobal", "url": project["url"], "platform": "darglobal", "key": "project"}]
    elif platform == "wasalt":
        reply["actions"] = [wasalt_search(f.get("purpose"), f.get("city"), f.get("property_type")), dest("wasalt_business")]
    else:
        reply["actions"] = [dest("darglobal_contact")]
    reply["suggested_replies"] = ["Keep browsing", "Start over"]
    return reply


def question_turn(s: Session, text: str, reply: dict) -> tuple[dict, list[dict] | None]:
    platform = s.filters.get("platform") if s.filters.get("platform") in ("darglobal", "wasalt") else None
    docs = rag.search(text, k=6)
    docs = docs[:5]
    reply["intent"] = {"name": "question", "platform": platform}
    if not docs or docs[0]["score"] < 0.25:
        reply["answer"] = ("I don't have reliable information on that in my DarGlobal and Wasalt sources. "
                           "I can help you search properties, explain a project, or connect you with an advisor.")
        reply["actions"] = [dest("darglobal_home"), dest("wasalt_home")]
        reply["suggested_replies"] = HOME_REPLIES[:4]
        return reply, None
    reply["sources"] = []
    seen = set()
    for d in docs:
        if d["url"] not in seen:
            seen.add(d["url"])
            reply["sources"].append({"title": d["title"], "url": d["url"], "platform": d["platform"]})
    props = [by_id(d["id"]) for d in docs[:3] if d["kind"] == "property" and d["score"] >= 0.55]
    props = [p for p in props if p][:4]
    if props:
        reply["recommendations"] = [card(p) for p in props]
        s.last_results = [p["id"] for p in props]
    top = by_id(docs[0]["id"]) if docs[0]["kind"] == "property" else None
    reply["answer"] = (f"**{top['title']}**: {top['description']}" if top else docs[0]["text"].split(". ", 1)[-1])[:600]
    reply["suggested_replies"] = ["Search properties", "Talk to an advisor", "Start over"]
    task = ("Answer the user's question using only CONTEXT, in 2-5 sentences. If CONTEXT only partly answers it, say what "
            "is known and what is not.")
    return reply, llm_messages(s, text, ctx_from_docs(docs), task, limit=130)


def greeting(s: Session, reply: dict) -> dict:
    reply["intent"] = {"name": "greeting"}
    reply["answer"] = ("Hello! I'm your property concierge for **DarGlobal** and **Wasalt**. I can find homes to buy or rent "
                       "across Saudi Arabia, show DarGlobal's branded residences worldwide, compare options and connect you "
                       "with an advisor. What are you looking for?")
    reply["suggested_replies"] = HOME_REPLIES
    return reply


# ----------------------------------------------------------------------------- entry point


def handle(message: str, session_id: str | None = None, compare_ids: list[str] | None = None) -> tuple[dict, list[dict] | None, Session]:
    """Return (structured reply, LLM messages to phrase the answer or None, session)."""
    s = get_session(session_id)
    text = message.strip()[:1200]
    reply = base_reply(s)
    contact_shared = bool(EMAIL.search(text) or PHONE.search(text))
    norm = apply_reply_shortcuts(text, s)
    # map platform quick replies
    low = norm.lower()
    if low in ("buy a home in saudi arabia", "rent in saudi arabia"):
        norm = "buy" if low.startswith("buy") else "rent"
        s.filters["platform"] = "wasalt"
    elif low in ("darglobal branded residences", "other countries"):
        norm = "darglobal"
        s.filters = {"platform": "darglobal"}
        s.asked.discard("country")
    elif low == "try another city":
        s.filters.pop("city", None)
        norm = "search"
    elif low in ("increase my budget",):
        if s.filters.get("budget_max") not in (None, "any"):
            s.filters["budget_max"] = s.filters["budget_max"] * 1.3
        norm = "search"
    elif low in ("lower my budget",):
        if s.filters.get("budget_max") not in (None, "any"):
            s.filters["budget_max"] = s.filters["budget_max"] * 0.75
        norm = "search"
    elif low in ("show villas instead", "show apartments instead"):
        s.filters["property_type"] = "villa" if "villa" in low else "apartment"
        s.filters.pop("bedrooms", None)
        norm = "search"
    elif low in ("similar projects", "show similar options") and s.last_project and by_id(s.last_project):
        lp = by_id(s.last_project)
        s.filters = {"platform": "darglobal", "country": lp["country"]}
        norm = "search"
    elif low in ("search properties", "keep browsing", "similar projects", "show similar options"):
        norm = "search"
    elif low in ("what else can you do?", "help"):
        norm = "hello"

    parsed = parse(norm)
    intent, slots = parsed["intent"], parsed["slots"]
    if norm == "search":
        intent = "search"
    if norm == "darglobal":
        intent = "search"
    # a bare answer to the question we just asked ("Riyadh", "3 bedrooms", "Buy") continues the search
    satisfies = {"country": ("country", "city", "brand"), "city": ("city",), "purpose": ("purpose",),
                 "property_type": ("property_type",), "bedrooms": ("bedrooms",), "budget_max": ("budget_max", "budget_min"),
                 "platform": ("platform", "purpose", "city", "country", "brand")}
    answered = "_any" in slots or any(k in slots for k in satisfies.get(s.awaiting or "", ()))
    if intent in ("question", "refine") and s.awaiting and answered:
        intent = "search"
    if low in ("compare the top two", "compare with another project") or compare_ids:
        intent = "compare"
    if low in ("register interest",):
        intent = "lead"
    if low in ("tell me about the first one",) and s.last_results:
        slots["project_id"] = s.last_results[0]
        intent = "project_info"
    if low in ("payment plans?",):
        intent = "project_info" if s.last_project else "question"
        slots.setdefault("project_id", s.last_project)

    if intent == "project_info":
        slots = {k: v for k, v in slots.items() if k in ("project_id",)}
    elif intent in ("question", "service", "compare", "lead", "greeting", "thanks"):
        # side questions don't rewrite the search the user is building
        slots = {k: v for k, v in slots.items() if k in ("project_id", "service")}
        s.awaiting = None
    changed = merge(s, slots, intent)
    reply["filters"] = public_filters(s)
    msgs = None

    if contact_shared and intent != "lead":
        intent = "lead"
    if intent == "greeting":
        reply = greeting(s, reply)
    elif intent == "thanks":
        reply["intent"] = {"name": "thanks"}
        reply["answer"] = "You're welcome! Anything else I can find for you?"
        reply["suggested_replies"] = HOME_REPLIES[:4]
    elif intent == "reset":
        reply = greeting(s, reply)
        reply["answer"] = "Done, I've cleared your preferences. " + reply["answer"].split("! ", 1)[-1]
    elif intent == "lead":
        if slots.get("project_id"):
            s.last_project = slots["project_id"]
        reply = lead_turn(s, reply)
        if contact_shared:
            reply["answer"] = ("For your privacy I haven't stored or forwarded the contact details you typed. Please use the "
                               "secure form below so you can confirm consent first.")
    elif intent == "compare":
        reply, msgs = compare_turn(s, norm, reply, compare_ids or [])
    elif intent == "service":
        reply, msgs = service_turn(s, norm, reply, slots["service"])
    elif intent == "project_info" and slots.get("project_id") and by_id(slots["project_id"]):
        reply, msgs = project_turn(s, norm, reply, by_id(slots["project_id"]))
    elif intent in ("search", "refine"):
        reply, msgs = search_turn(s, norm, reply)
    else:
        reply, msgs = question_turn(s, text, reply)

    reply["filters"] = public_filters(s)
    s.history.append({"role": "user", "content": redact(text)[:500]})
    return reply, msgs, s


def remember_answer(s: Session, answer: str) -> None:
    s.history.append({"role": "assistant", "content": answer[:600]})
    s.history = s.history[-8:]
