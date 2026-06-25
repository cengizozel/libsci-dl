"""libsci-dl — resolve and download books/papers by identifier.

Sources: Library Genesis (ISBN), Unpaywall + PubMed Central + Sci-Hub (DOI),
arXiv, and direct URLs.
"""
from __future__ import annotations

__version__ = "0.1.0"

from .core import Engine          # noqa: E402
from .download import Downloader  # noqa: E402
from .identify import detect      # noqa: E402
from .models import Candidate, FetchMethod, IdType, Result  # noqa: E402

__all__ = [
    "Engine", "Downloader", "detect",
    "Candidate", "FetchMethod", "IdType", "Result", "__version__",
]
