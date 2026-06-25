# Library API

Everything the CLI does is available as a Python API.

## Quick start

```python
from libsci_dl import Engine

engine = Engine(out_dir="downloads", email="you@example.com")
results = engine.run(["9780471433347", "10.1038/323533a0", "1706.03762"])
for r in results:
    print(r.status, r.identifier, r.path or r.error)
engine.close()
```

`run` also accepts `(identifier, title)` pairs, where the title is used to name
the saved file:

```python
engine.run([("10.1038/323533a0", "Backprop"), ("1706.03762", "Attention")])
```

## Engine

```python
Engine(
    out_dir="downloads",
    manifest_path=None,          # default: <out_dir>/manifest.tsv
    email="anonymous@example.com",
    url_only=False,
    size_cap=80.0,               # MB; book edition preference
    scihub=True,                 # include the Sci-Hub fallback
    downloader=None,             # supply a configured Downloader, or one is made
    verbose=False,
    on_result=None,              # callback(Result) called as each item finishes
)
```

Methods:

- `process(raw, title="")` returns a `Result`: resolve and (unless `url_only`)
  download a single identifier. Does not touch the manifest.
- `resolve(identifier, id_type, title="")` returns the list of candidate URLs.
- `run(items, workers=1, resume=True)` returns a list of `Result`: process a
  batch, record to the manifest, and skip already-done items unless
  `resume=False`. Skipped items are omitted from the returned list.
- `close()` flushes the manifest and quits the browser. Call it when done, or use
  a `try/finally`.

## Downloader

Construct one to share across engines or to customize behavior:

```python
from libsci_dl import Downloader

dl = Downloader(
    user_agent=...,        # default is a Chrome UA string
    read_timeout=60,       # seconds between bytes on an HTTP read
    file_deadline=600,     # max seconds for one HTTP download
    browser_wait=40,       # seconds to wait for a browser download
    tmp_dir=None,          # scratch dir; default ~/.cache/libsci-dl/parts
    cookies={},            # dict of cookies applied to HTTP requests
    insecure=False,        # True disables TLS verification
    verbose=False,
)
engine = Engine(downloader=dl)
```

- `session()` returns the calling thread's `requests.Session`.
- `fetch(candidate, dest_no_ext)` downloads one candidate and returns the saved
  path, or `None`. The extension is appended from magic bytes.
- The browser is created lazily on first use and reused; `close()` quits it.

## Manifest

```python
from libsci_dl.manifest import Manifest

m = Manifest("downloads/manifest.tsv")
m.is_done("10.1038/323533a0")   # True if previously downloaded
m.counts()                       # {"ok": 120, "not_found": 7, ...}
```

## Data types

```python
from libsci_dl import IdType, FetchMethod, Candidate, Result, detect

detect("978-0-471-43334-7")      # (IdType.ISBN, "9780471433347")
detect("10.1038/323533a0")       # (IdType.DOI, "10.1038/323533a0")
```

- `IdType` - `ISBN`, `DOI`, `ARXIV`, `URL`, `UNKNOWN`.
- `FetchMethod` - `REQUESTS`, `SELENIUM`, `SELENIUM_SCIHUB`.
- `Candidate(url, source, method=REQUESTS, ext="pdf", note="")` - one place to
  try.
- `Result(identifier, id_type, title, status, path, source, nbytes, error,
  candidates)` - the outcome. `status` is one of `ok`, `not_found`, `error`,
  `url_only`. `as_row()` returns the manifest dict.

## url-only from code

```python
engine = Engine(out_dir="review", url_only=True)
for r in engine.run(my_ids):
    print(r.identifier, [c.url for c in r.candidates])
```
