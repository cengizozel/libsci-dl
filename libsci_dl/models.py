"""Shared data types."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IdType(str, Enum):
    ISBN = "isbn"
    DOI = "doi"
    ARXIV = "arxiv"
    URL = "url"
    UNKNOWN = "unknown"


class FetchMethod(str, Enum):
    """How a candidate URL should be fetched."""
    REQUESTS = "requests"          # plain HTTP GET, expect a PDF
    SELENIUM = "selenium"          # load in a real browser and let it download (beats anti-bot)
    SELENIUM_SCIHUB = "selenium_scihub"  # load a Sci-Hub article page, extract the embedded PDF, download


@dataclass
class Candidate:
    """A possible place to download a document from."""
    url: str
    source: str                    # e.g. "libgen.li", "unpaywall", "pmc", "scihub", "arxiv"
    method: FetchMethod = FetchMethod.REQUESTS
    ext: str = "pdf"               # expected file extension
    note: str = ""                 # human-readable context (edition, size, ...)


@dataclass
class Result:
    identifier: str
    id_type: IdType
    title: str = ""
    status: str = "pending"        # ok | not_found | error | url_only
    path: Optional[str] = None     # saved file path when downloaded
    source: str = ""               # winning source
    nbytes: int = 0
    error: str = ""
    candidates: list[Candidate] = field(default_factory=list)

    def as_row(self) -> dict:
        return {
            "identifier": self.identifier,
            "type": self.id_type.value,
            "status": self.status,
            "source": self.source,
            "path": self.path or "",
            "bytes": self.nbytes,
            "title": self.title,
        }
