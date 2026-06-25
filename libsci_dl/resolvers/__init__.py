"""Resolvers turn an identifier into a list of download Candidates.

Each resolver is a callable ``resolve(identifier, title="", http=session)`` that
returns a list of Candidate objects. The registry maps an IdType to an ordered
list of resolvers; earlier resolvers are preferred (legal open access before
Sci-Hub).
"""
from __future__ import annotations

from ..models import IdType
from . import arxiv, doi_pmc, doi_scihub, doi_unpaywall, isbn_libgen, url

REGISTRY = {
    IdType.ISBN: [isbn_libgen.resolve],
    IdType.DOI: [doi_unpaywall.resolve, doi_pmc.resolve, doi_scihub.resolve],
    IdType.ARXIV: [arxiv.resolve],
    IdType.URL: [url.resolve],
}


def resolvers_for(id_type: IdType):
    return REGISTRY.get(id_type, [])
