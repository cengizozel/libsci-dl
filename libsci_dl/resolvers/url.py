"""A raw URL -> try it directly, plus a few obvious PDF derivations.

Some inputs are already direct PDFs (good); others are landing pages where the
PDF lives at a predictable sibling URL (JMLR ``.html`` -> ``.pdf``, RFC editor,
NASA NTRS). The Selenium fallback in the downloader covers the rest.
"""
from __future__ import annotations

import re

from ..models import Candidate, FetchMethod


def _derivations(url: str) -> list[str]:
    out = []
    if re.search(r"\.html?$", url, re.I):
        out.append(re.sub(r"\.html?$", ".pdf", url, flags=re.I))
    m = re.search(r"rfc-editor\.org/rfc/rfc(\d+)", url)
    if m:
        out.append(f"https://www.ietf.org/rfc/rfc{m.group(1)}.txt.pdf")
    m = re.search(r"ntrs\.nasa\.gov/citations/(\d+)", url)
    if m:
        out.append(f"https://ntrs.nasa.gov/api/citations/{m.group(1)}/downloads/{m.group(1)}.pdf")
    return out


def resolve(identifier: str, title: str = "", http=None) -> list[Candidate]:
    url = identifier.strip()
    cands = [Candidate(url=url, source="url", method=FetchMethod.REQUESTS)]
    for d in _derivations(url):
        cands.append(Candidate(url=d, source="url:derived", method=FetchMethod.REQUESTS))
    # last resort: load the original page in a browser (handles JS / anti-bot)
    cands.append(Candidate(url=url, source="url:browser", method=FetchMethod.SELENIUM))
    return cands
