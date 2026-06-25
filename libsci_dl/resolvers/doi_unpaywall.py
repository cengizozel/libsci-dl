"""DOI to Unpaywall (legal open access).

Unpaywall indexes open-access copies of paywalled articles. This is the first
DOI resolver tried because it is legal and free. Many candidates are direct
PDFs on publisher / repository / PMC servers; some are HTML landing pages, which
the Selenium fallback in the downloader handles.
"""
from __future__ import annotations

from urllib.parse import quote

from ..models import Candidate, FetchMethod

API = "https://api.unpaywall.org/v2/{doi}?email={email}"


def resolve(identifier: str, title: str = "", http=None, email: str = "anonymous@example.com") -> list[Candidate]:
    if http is None:
        import requests
        http = requests.Session()
        http.verify = False
    doi = identifier.strip()
    try:
        data = http.get(API.format(doi=quote(doi, safe="/"), email=email), timeout=20).json()
    except Exception:
        return []
    out: list[Candidate] = []
    seen: set[str] = set()
    locations = [data.get("best_oa_location")] + (data.get("oa_locations") or [])
    for loc in locations:
        if not loc:
            continue
        # url_for_pdf is a direct PDF; url is the landing page (browser fallback)
        for url, kind in ((loc.get("url_for_pdf"), FetchMethod.REQUESTS),
                          (loc.get("url"), FetchMethod.SELENIUM)):
            if not url or url in seen:
                continue
            seen.add(url)
            host = loc.get("host_type") or "oa"
            out.append(Candidate(url=url, source=f"unpaywall:{host}", method=kind))
    return out
