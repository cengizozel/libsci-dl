# Troubleshooting

## The browser sources do nothing

Sci-Hub and PubMed Central need a real browser. If Chrome or Chromium and
chromedriver are not available, the browser engine is disabled after the first
failure and only the HTTP sources (ISBN via Libgen, arXiv, direct PDFs, and any
open-access direct PDFs) work. Run with `--verbose` to see a
"browser unavailable" line.

Fixes:

- Install Chromium or Chrome and chromedriver, and make sure both are on your
  PATH. On many systems Selenium 4 can fetch a matching driver itself.
- Confirm the driver version matches the browser version.
- In a container, the launch flags `--no-sandbox` and `--disable-dev-shm-usage`
  are already set; you still need the browser binary present.

## Everything from Sci-Hub fails or returns stubs

Sci-Hub uses DDoS-Guard. Symptoms of a rate-limit or ban are tiny stub pages
and repeated misses.

- Lower `--workers`. Parallel hits trip the limit faster.
- Wait. The throttle is cumulative per IP and clears over time.
- Pass a clearance cookie with `--cookies`. Export the Sci-Hub cookies from a
  browser where the site loads (a `cookies.txt` or JSON export both work). Note
  these cookies are short-lived and tied to your IP, so they are a temporary aid,
  not a permanent fix.
- Use `--no-scihub` to skip it and rely on open access only.

## A download saved as the wrong type, or nothing saved

The extension is taken from the file's magic bytes, so a PDF is named `.pdf`, a
DjVu `.djvu`, and an EPUB `.epub` regardless of the URL. If a source returned an
HTML error page, verification rejects it and nothing is saved for that
candidate; the next candidate is tried. A final `not_found` means no candidate
produced a real document.

## A specific item is missing

Coverage is not complete:

- Very new papers may not be on Sci-Hub yet, and may have no open-access copy.
- Some books are not on the reachable Libgen mirrors.
- A publisher landing page may block even the browser.

Run that single identifier with `--verbose` to see which candidates were tried
and why each failed. In `--url-only` mode you can inspect the candidate links
directly in `urls.tsv`.

## TLS certificate errors

Verification is on by default. If a mirror has a genuinely broken certificate
and you accept the risk, pass `--insecure` to disable verification. Prefer
fixing the system trust store first.

## Re-running re-downloads everything (or skips everything)

The manifest at `<out>/manifest.tsv` records progress. By default a re-run skips
items already marked `ok`. Use `--no-resume` to force a full re-run, or point
`--manifest` at a different file to keep separate histories. If you deleted the
output files but kept the manifest, the items still count as done; delete the
manifest too, or use `--no-resume`, to fetch them again.

## Slow runs

The browser sources are inherently slow (a page load plus a challenge per item).
HTTP sources benefit from more `--workers`; the browser is serialised regardless,
so very high worker counts mainly speed up ISBN, arXiv, and open-access HTTP
downloads.
