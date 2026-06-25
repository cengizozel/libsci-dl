"""DOI to PubMed Central (free full text for biomedical literature).

NCBI's ID-converter maps a DOI to a PMCID; PMC then has a free PDF at
``/articles/<PMCID>/pdf/``. PMC serves an anti-bot interstitial to plain HTTP,
so this candidate is marked for the Selenium engine, which downloads it the way
a real browser does.
"""
from __future__ import annotations

from urllib.parse import quote

from ..models import Candidate, FetchMethod

IDCONV = ("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
          "?ids={doi}&format=json&tool=libsci-dl&email={email}")


def resolve(identifier: str, title: str = "", http=None, email: str = "anonymous@example.com") -> list[Candidate]:
    if http is None:
        import requests
        http = requests.Session()
        http.verify = False
    doi = identifier.strip()
    try:
        data = http.get(IDCONV.format(doi=quote(doi, safe="/"), email=email), timeout=20).json()
    except Exception:
        return []
    records = data.get("records") or []
    pmcid = records[0].get("pmcid") if records else None
    if not pmcid:
        return []
    return [Candidate(
        url=f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/",
        source=f"pmc:{pmcid}",
        method=FetchMethod.SELENIUM,
    )]
