"""Detect and normalize the type of an identifier string."""
from __future__ import annotations

import re

from .models import IdType

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
_DOI_IN_URL_RE = re.compile(r"(10\.\d{4,9}/[^\s?#]+)", re.I)
# modern arXiv: 2301.01234 (optionally vN); legacy: math.GT/0512018 or hep-th/9901001
_ARXIV_NEW_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_ARXIV_OLD_RE = re.compile(r"^[a-z-]+(\.[A-Za-z-]+)?/\d{7}(v\d+)?$", re.I)


def _clean_isbn(s: str) -> str:
    return re.sub(r"[^0-9Xx]", "", s)


def _valid_isbn(digits: str) -> bool:
    if len(digits) == 13 and digits.isdigit():
        return digits.startswith(("978", "979"))
    if len(digits) == 10:
        # last char may be X
        return bool(re.fullmatch(r"\d{9}[\dXx]", digits))
    return False


def detect(raw: str) -> tuple[IdType, str]:
    """Return (IdType, normalized_identifier) for a raw input string."""
    s = raw.strip()
    if not s:
        return IdType.UNKNOWN, s

    low = s.lower()

    # Explicit prefixes people paste
    if low.startswith("doi:"):
        return IdType.DOI, s[4:].strip()
    if low.startswith("arxiv:"):
        return IdType.ARXIV, s[6:].strip()
    if low.startswith(("isbn:", "isbn-13:", "isbn-10:")):
        s = s.split(":", 1)[1].strip()
        low = s.lower()

    # URLs — but a doi.org / arxiv.org URL is better treated as its identifier
    if low.startswith(("http://", "https://", "www.")):
        m = _DOI_IN_URL_RE.search(s)
        if "doi.org/" in low and m:
            return IdType.DOI, m.group(1)
        am = re.search(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:\.pdf)?$", s, re.I)
        if am:
            return IdType.ARXIV, am.group(1)
        return IdType.URL, s

    if _DOI_RE.match(s):
        return IdType.DOI, s

    if _ARXIV_NEW_RE.match(s) or _ARXIV_OLD_RE.match(s):
        return IdType.ARXIV, s

    digits = _clean_isbn(s)
    if _valid_isbn(digits):
        return IdType.ISBN, digits

    # A bare DOI sometimes lacks the leading "10." check above; last resort
    m = _DOI_IN_URL_RE.search(s)
    if m:
        return IdType.DOI, m.group(1)

    return IdType.UNKNOWN, s
