"""DOI to Sci-Hub (last-resort fallback).

Sci-Hub sits behind DDoS-Guard, whose JavaScript challenge plain ``requests``
cannot solve (it gets a tiny stub/captcha page and a cumulative IP ban). A real
headless browser solves the challenge, so this candidate is marked
``SELENIUM_SCIHUB``: the downloader loads the article page in the browser,
extracts the embedded ``citation_pdf_url``, and downloads it.

Mirrors are tried in order. ``sci-hub.ist`` is first because it was the most
reliable in practice; adjust ``MIRRORS`` if availability changes.
"""
from __future__ import annotations

from urllib.parse import quote

from ..models import Candidate, FetchMethod

MIRRORS = ["https://sci-hub.ist", "https://sci-hub.st", "https://sci-hub.ru"]


def resolve(identifier: str, title: str = "", http=None, mirrors: list[str] | None = None) -> list[Candidate]:
    doi = quote(identifier.strip(), safe="/")
    out = []
    for mirror in (mirrors or MIRRORS):
        out.append(Candidate(
            url=f"{mirror}/{doi}",
            source=f"scihub:{mirror.split('//', 1)[-1]}",
            method=FetchMethod.SELENIUM_SCIHUB,
        ))
    return out
