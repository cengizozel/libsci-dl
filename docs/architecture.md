# Architecture

## Pipeline

For each identifier:

1. Detect the type (`identify.py`), producing an `IdType` and a normalized
   identifier.
2. Run the resolvers for that type (`resolvers/`), producing a list of
   candidates, with legal sources first.
3. In url-only mode, record the candidates and stop here.
4. Otherwise download the candidates in order (`download.py`); the first one
   that yields a verified file wins. The HTTP engine runs first, with a browser
   fallback.
5. Record the outcome in the manifest (`manifest.py`), the resumable ledger that
   is the source of truth.

## Modules

| Module | Responsibility |
|--------|----------------|
| `identify.py` | Detect ISBN / DOI / arXiv / URL from a raw string and normalize it. Pure, no network. |
| `models.py` | Data types: `IdType`, `FetchMethod`, `Candidate`, `Result`. |
| `resolvers/` | One module per source. Each exposes a `resolve(identifier, title="", http=None, ...)` function that returns a list of candidates. `resolvers/__init__.py` maps each `IdType` to an ordered list of resolvers. |
| `download.py` | `Downloader` with two engines (HTTP via `requests`, and a headless browser via Selenium), magic-byte verification, per-file deadlines. |
| `core.py` | `Engine` ties resolvers, downloader, and manifest together; handles batching, concurrency, resume, and per-item error isolation. |
| `cli.py` | Argument parsing, input reading, cookie loading, progress output. |

## Candidate and the two engines

A `Candidate` carries a URL, a `source` label, and a `FetchMethod`:

- `REQUESTS` - plain HTTP GET; if it does not yield a verified file, the
  downloader automatically retries the same URL through the browser.
- `SELENIUM` - load the URL in the headless browser and let it download the file
  (handles anti-bot and JavaScript pages, for example PubMed Central).
- `SELENIUM_SCIHUB` - load a Sci-Hub article page in the browser, extract the
  embedded `citation_pdf_url`, and download that.

`Downloader.fetch(candidate, dest_no_ext)` returns the saved path or `None`. The
extension is decided by magic bytes (`%PDF-`, `AT&TFORM` for DjVu, `PK\x03\x04`
for EPUB), never by the URL, so an HTML error page is never saved as a document.

## Verification

`verify_file` reads the first bytes of a freshly downloaded temporary file and
returns its true extension, or `None` if it is not a recognized document or is
smaller than 1 KB. Only verified files are moved into place; failures are
deleted and the next candidate is tried.

## Concurrency model

`Engine.run(items, workers=N)` processes items with a thread pool when `N > 1`.

- HTTP uses one `requests.Session` per thread (thread-local), so parallel HTTP
  downloads are safe.
- The headless browser is a single shared instance guarded by a lock, so browser
  work is serialised even under many workers. This parallelises the fast HTTP
  sources while keeping the slow, single browser correct.
- The manifest is guarded by a lock and flushed periodically and at the end.

Because Sci-Hub and PubMed Central are browser-bound and rate-sensitive, very
high worker counts mostly help ISBN, arXiv, and open-access HTTP downloads.

## Resumable manifest

`manifest.py` writes a tab-separated ledger (`identifier  type  status  source
path  bytes  title`). On startup it is loaded; `is_done` reports `ok` items,
which are skipped on the next run unless `--no-resume` is given. The manifest is
trusted over the filesystem, so files that have been moved or uploaded elsewhere
are not re-downloaded. Field values are sanitized on write so a title containing
a tab or newline cannot corrupt the table.

## Error isolation

Each item is processed inside a guard, so an unexpected failure on one
identifier is recorded as an `error` result and the batch continues. A missing
browser is detected once and disables only the browser engine for the rest of
the run; HTTP-based sources keep working.
