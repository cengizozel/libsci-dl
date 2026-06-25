# Extending: add a new source

A source is a resolver: a function that turns an identifier into a list of
candidate download locations. You do not write any download code; the engine
handles fetching, the browser fallback, verification, and the manifest.

## The resolver contract

```python
def resolve(identifier: str, title: str = "", http=None, **opts):
    # returns a list of Candidate objects, best first
    ...
```

- `identifier` is the normalized identifier (for example a bare DOI or ISBN).
- `title` is an optional title, available if useful.
- `http` is a `requests.Session` you may reuse for lookups. If `None`, create
  your own.
- `**opts` may include `email` and `size_cap`. The engine inspects your
  signature and passes only the keyword arguments you declare, so accept just
  what you need.

Return a list of `Candidate` objects, best first. Returning an empty list means
"this source has nothing".

## Candidate

```python
from libsci_dl.models import Candidate, FetchMethod

Candidate(
    url="https://example.org/paper.pdf",
    source="example",                 # short label recorded in the manifest
    method=FetchMethod.REQUESTS,      # how to fetch it (see below)
    ext="pdf",                        # hint only; real ext comes from magic bytes
    note="",                          # optional human-readable context
)
```

Choose a `FetchMethod`:

- `REQUESTS` for a direct file link. If it does not download cleanly, the engine
  retries it in the browser automatically, so this is the right default for most
  links, including ones that sometimes sit behind a script wall.
- `SELENIUM` when the link is a page that must run JavaScript or pass an anti-bot
  check before the file appears.
- `SELENIUM_SCIHUB` for a Sci-Hub-style article page where the PDF link is
  embedded as `citation_pdf_url` in the page HTML.

## Register it

Add your resolver to the registry in `libsci_dl/resolvers/__init__.py`:

```python
from . import my_source

REGISTRY = {
    IdType.DOI: [doi_unpaywall.resolve, my_source.resolve, doi_scihub.resolve],
    ...
}
```

Order matters: earlier resolvers are preferred, so place legal or fast sources
before slower or last-resort ones.

## Example

A minimal resolver that offers a publisher PDF for a DOI:

```python
# libsci_dl/resolvers/my_source.py
from ..models import Candidate, FetchMethod

def resolve(identifier, title="", http=None):
    return [Candidate(
        url=f"https://example.org/pdf/{identifier}",
        source="example",
        method=FetchMethod.REQUESTS,
    )]
```

That is all that is needed; the engine takes it from there.

## Tips

- Keep network lookups inside the resolver defensive; wrap them in
  `try/except` and return an empty list on failure. The engine already guards
  resolver calls, but failing quietly keeps a flaky API from slowing a batch.
- Do not download in a resolver. Return URLs and let the downloader verify the
  bytes, so a wrong or blocked link is handled uniformly.
- If your source is rate-sensitive, document it; the engine does not throttle
  per host.
