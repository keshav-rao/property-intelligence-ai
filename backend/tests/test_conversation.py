"""Behaviour tests for understanding, the guided workflow and the safety rules.

Run:  cd backend && python -m pytest -q
These tests never call the LLM: dialogue.handle() builds the structured reply first.
"""
import os

os.environ.setdefault("QDRANT_URL", ":memory:")

import pytest

from app import dialogue
from app.catalog import load_catalog
from app.nlu import parse, parse_bedrooms, parse_budget


def chat(*messages):
    sid, rep = None, None
    for m in messages:
        rep, _, s = dialogue.handle(m, sid)
        sid = s.id
    return rep


# ----------------------------------------------------------------- understanding

@pytest.mark.parametrize("text,expected", [
    ("under 1.2 million", (None, 1_200_000)),
    ("budget 900k", (None, 900_000)),
    ("between 1M and 2M", (1_000_000, 2_000_000)),
    ("max SAR 40,000", (None, 40_000)),
    ("3 bedroom villa", (None, None)),
])
def test_budget(text, expected):
    assert parse_budget(text) == expected


@pytest.mark.parametrize("text,expected", [("3 bed", 3), ("three bedrooms", 3), ("a studio", 0), ("2BR flat", 2), ("villa", None)])
def test_bedrooms(text, expected):
    assert parse_bedrooms(text) == expected


def test_full_request_is_understood():
    p = parse("I want to buy a 3 bedroom apartment in Riyadh under 1.2 million")
    assert p["intent"] == "search"
    expected = {"purpose": "sale", "city": "riyadh", "property_type": "apartment", "bedrooms": 3, "budget_max": 1_200_000}
    assert p["slots"].items() >= expected.items()


def test_project_names_and_nicknames():
    assert parse("Tell me about Les Vagues")["slots"]["project_id"].startswith("dg-les-vagues")
    assert parse("what about trump tower dubai")["slots"]["project_id"].startswith("dg-trump-international-hotel")
    assert "project_id" not in parse("London Stock Exchange results")["slots"]


# ----------------------------------------------------------------- data honesty

def test_darglobal_never_has_invented_prices():
    for x in load_catalog():
        if x["platform"] == "darglobal":
            assert x["price"] is None and x["price_label"] == "Price on request"
            assert x["url"].startswith("https://darglobal.co.uk/")


def test_wasalt_items_are_attributed_and_linked():
    ws = [x for x in load_catalog() if x["platform"] == "wasalt"]
    assert len(ws) > 100
    assert all(x["url"].startswith("https://wasalt.sa/en/property/") and x["source"] == "Wasalt.sa" for x in ws)
    assert all(x["available"] is None for x in ws)  # a snapshot is not proof of availability


# ----------------------------------------------------------------- guided workflow

def test_asks_only_for_missing_details_then_recommends():
    rep = chat("I want to buy a property in Riyadh")
    assert rep["intent"]["step"] == "ask_property_type"
    rep = chat("I want to buy a property in Riyadh", "Apartment", "3 bedrooms", "Up to SAR 1.2M")
    assert rep["intent"]["step"] == "results"
    assert rep["recommendations"], "expected listings"
    for c in rep["recommendations"]:
        assert c["platform"] == "wasalt" and c["city"] == "Riyadh" and c["purpose"] == "sale" and c["price"] <= 1_200_000
    assert any(a["url"] == "https://wasalt.sa/en/apartments-for-sale-in-riyadh" for a in rep["actions"])


def test_user_can_change_their_mind():
    rep = chat("rent a villa in Jeddah under 100k", "Any", "Show apartments instead")
    assert rep["filters"]["property_type"] == "apartment"
    assert rep["filters"]["city"] == "jeddah"


def test_new_request_starts_a_fresh_search():
    rep = chat("Show me Trump projects in Jeddah", "3 bed apartment for rent in Dammam")
    assert "brand" not in rep["filters"] and rep["filters"]["city"] == "dammam"


def test_side_question_does_not_change_the_search():
    rep = chat("studio in khobar", "What is REGA?")
    assert rep["intent"]["name"] == "question"
    assert rep["filters"]["city"] == "khobar"


def test_luxury_abroad_routes_to_darglobal():
    rep = chat("I want a luxury villa in Spain")
    assert rep["intent"]["platform"] == "darglobal"
    assert {c["title"].split(",")[0] for c in rep["recommendations"]} >= {"Tierra Viva"}


def test_compare_two_named_projects():
    rep = chat("compare DG1 and Les Vagues")
    assert rep["ui"]["type"] == "compare"
    assert [c["title"] for c in rep["ui"]["columns"]] == ["DG1", "Les Vagues by Elie Saab"]


# ----------------------------------------------------------------- navigation + privacy

def test_services_link_to_official_pages():
    assert chat("How do Wasalt auctions work?")["actions"][0]["url"] == "https://auction.wasalt.sa/en"
    assert chat("I want to list my property")["actions"][0]["url"] == "https://wasalt.sa/en/post-property"


def test_contact_details_typed_in_chat_open_the_form_and_are_redacted():
    rep, msgs, s = dialogue.handle("my email is someone@example.com, call me on +966 55 123 4567", None)
    assert rep["ui"]["type"] == "lead_form"
    assert msgs is None
    assert all("example.com" not in h["content"] and "4567" not in h["content"] for h in s.history)


def test_unknown_topics_are_declined_not_invented():
    rep = chat("Do you have apartments on Mars?")
    assert rep["recommendations"] == []
