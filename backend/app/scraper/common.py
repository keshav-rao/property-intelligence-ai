"""Shared polite-scraping utilities.

Rules enforced here for every request:
  * honest, identifiable User-Agent (no browser impersonation)
  * robots.txt is fetched and obeyed per host
  * fixed delay between requests
  * transport is the stock `curl` binary with default settings: no TLS/browser
    fingerprint impersonation of any kind
  * bot-challenge / CAPTCHA pages are detected and treated as "access denied";
    we never attempt to solve or work around them
"""
from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = "PropertyIntelligenceResearchBot/1.0 (educational RAG demo; low-rate; public pages only)"
REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw"

CHALLENGE_MARKERS = ("_Incapsula_Resource", "cf-challenge", "captcha-delivery", "g-recaptcha", "hcaptcha")


class AccessDenied(Exception):
    """The site declined automated access (robots.txt, bot challenge, 401/403/429)."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def looks_like_challenge(body: str) -> bool:
    head = body[:5000]
    return len(body) < 5000 and any(m in head for m in CHALLENGE_MARKERS)


class PoliteClient:
    def __init__(self, delay: float = 2.0, timeout: int = 40):
        self.delay = delay
        self.timeout = timeout
        self._last = 0.0
        self._robots: dict[str, RobotFileParser | None] = {}

    def _wait(self) -> None:
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()

    def _fetch(self, url: str) -> tuple[int, bytes]:
        self._wait()
        proc = subprocess.run(
            ["curl", "-sS", "-L", "--compressed", "-m", str(self.timeout), "-A", USER_AGENT,
             "-H", "Accept-Language: en", "-w", "\n%{http_code}", url],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise OSError(f"curl failed for {url}: {proc.stderr.decode(errors='replace').strip()}")
        body, _, code = proc.stdout.rpartition(b"\n")
        return int(code or 0), body

    def _robots_for(self, url: str) -> RobotFileParser | None:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp: RobotFileParser | None = None
            try:
                code, body = self._fetch(base + "/robots.txt")
                text = body.decode("utf-8", errors="replace")
                if code == 200 and not looks_like_challenge(text):
                    rp = RobotFileParser()
                    rp.parse(text.splitlines())
            except OSError:
                rp = None
            self._robots[base] = rp
        return self._robots[base]

    def robots_readable(self, url: str) -> bool:
        return self._robots_for(url) is not None

    def get(self, url: str, check_robots: bool = True) -> str:
        if check_robots:
            rp = self._robots_for(url)
            if rp is not None and not rp.can_fetch(USER_AGENT, url):
                raise AccessDenied(f"robots.txt disallows {url}")
        code, body = self._fetch(url)
        text = body.decode("utf-8", errors="replace")
        if code in (401, 403, 429) or looks_like_challenge(text) or "<title>Just a moment" in text[:600]:
            raise AccessDenied(f"access denied (HTTP {code} / bot challenge) for {url}")
        if code != 200:
            raise OSError(f"HTTP {code} for {url}")
        return text

    def get_bytes(self, url: str) -> bytes:
        code, body = self._fetch(url)
        if code != 200:
            raise OSError(f"HTTP {code} for {url}")
        return body

    def close(self) -> None:
        pass
