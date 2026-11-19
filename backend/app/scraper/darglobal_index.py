"""Rebuild the DarGlobal project list from darglobal.co.uk/projects.

darglobal.co.uk sits behind an Imperva/Incapsula bot challenge, so automated HTTP clients
get a challenge page instead of content. We do not solve or bypass that challenge.
Instead, open https://darglobal.co.uk/projects in a normal browser, save the page
("Save page as… → HTML only") to data/raw/darglobal/projects_page.html, and run:

    python -m app.scraper.darglobal_index

The project cards are read from the page's own __NEXT_DATA__ JSON (title, location,
bedrooms, type, completion date, image, link). The descriptions in projects_live.json
were then taken from each project's official page. DarGlobal publishes no prices on
these pages, so no prices are recorded.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data" / "raw" / "darglobal" / "projects_page.html"
OUT = ROOT / "data" / "raw" / "darglobal" / "projects_index.json"
NEXT = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def parse(html: str) -> list[dict]:
    m = NEXT.search(html)
    if not m:
        raise SystemExit("No __NEXT_DATA__ found. Was the page saved after it fully loaded?")
    tabs = json.loads(m.group(1))["props"]["pageProps"]["pageData"]["attributes"]["Tabs"]
    rows = []
    for tab in tabs:
        for d in tab.get("TabData") or []:
            img = (((d.get("ProjectCardImage") or {}).get("data") or {}).get("attributes") or {})
            rows.append({
                "title": (d.get("ProjectTitle") or "").strip(),
                "country": tab.get("TabHeading"),
                "location": d.get("Location"),
                "bedrooms": (d.get("Bedrooms") or "").strip() or None,
                "type": d.get("ProjectType"),
                "completion": d.get("completionDate"),
                "url": "https://darglobal.co.uk" + d["Link"] if d.get("Link") else None,
                "image": ((img.get("formats") or {}).get("medium") or {}).get("url") or img.get("url"),
            })
    return rows


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    rows = parse(src.read_text(encoding="utf-8"))
    OUT.write_text(json.dumps({"source": "https://darglobal.co.uk/projects", "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "projects": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} projects -> {OUT}")


if __name__ == "__main__":
    main()
