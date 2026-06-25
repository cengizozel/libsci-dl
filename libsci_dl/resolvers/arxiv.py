"""arXiv — fully open access, just construct the PDF URL."""
from __future__ import annotations

from ..models import Candidate, FetchMethod


def resolve(identifier: str, title: str = "", http=None) -> list[Candidate]:
    arxiv_id = identifier.strip()
    return [Candidate(
        url=f"https://arxiv.org/pdf/{arxiv_id}",
        source="arxiv",
        method=FetchMethod.REQUESTS,
    )]
