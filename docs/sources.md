# Sources

For each identifier type, one or more resolvers produce candidate download URLs.
The downloader tries them in order and keeps the first that yields a file whose
magic bytes confirm it is a real document. This page explains each source.

## ISBN: Library Genesis

Module: `libsci_dl/resolvers/isbn_libgen.py`. Mirrors tried, in order:
`https://libgen.li`, `https://libgen.vg`.

Flow:

1. `GET {mirror}/index.php?req=<ISBN>` returns a results table. Each row is
   parsed into title, language, size, extension, and an MD5.
2. The best row is chosen (see below) and `GET {mirror}/ads.php?md5=<MD5>`
   returns a page containing the real `get.php?md5=...&key=...` link.
3. That `get.php` link is the download URL (a `requests` candidate).

### Edition selection

`_pick` ranks rows by this key, highest wins:

1. under the size cap (`--size-cap`, default 80 MB) or not
2. format rank: PDF, then EPUB, then DjVu, then MOBI and AZW3
3. English or not
4. smallest file

Putting the size cap first means a small EPUB or DjVu is chosen over a giant PDF
scan when the only PDF is oversized; among under-cap files, PDF is preferred, and
ties break toward the smallest. This is deliberate: bandwidth is the limiting
factor, and a compact text edition finishes where a 150 MB scan stalls.

### Notes

- `libgen.is` and `libgen.rs` were unreachable during development and are not in
  the mirror list; `libgen.gs` returned block stubs. Adjust `MIRRORS` if
  availability changes.
- Result files may be PDF, DjVu, or EPUB; the extension is set from magic bytes.

## DOI: Unpaywall, then PubMed Central, then Sci-Hub

A DOI is tried against three resolvers in order. Resolution stops at download
time on the first candidate that produces a verified file, so the legal sources
are exhausted before Sci-Hub.

### Unpaywall (open access)

Module: `doi_unpaywall.py`. Calls `https://api.unpaywall.org/v2/<doi>?email=...`
and turns every open-access location into candidates: a `url_for_pdf` becomes a
direct `requests` candidate, and a landing-page `url` becomes a browser
candidate (some publisher pages need JavaScript). This is legal and free; set a
real `--email`.

### PubMed Central

Module: `doi_pmc.py`. Uses the NCBI ID converter
(`/pmc/utils/idconv/v1.0/?ids=<doi>`) to map the DOI to a PMCID, then offers
`https://pmc.ncbi.nlm.nih.gov/articles/<PMCID>/pdf/` as a browser candidate. PMC
serves an anti-bot interstitial to plain HTTP, so this is downloaded through the
headless browser, which gets the real PDF.

### Sci-Hub

Module: `doi_scihub.py`. Mirrors, in order: `sci-hub.ist`, `sci-hub.st`,
`sci-hub.ru`. Each mirror becomes a `SELENIUM_SCIHUB` candidate. Sci-Hub sits
behind DDoS-Guard, whose JavaScript challenge plain `requests` cannot solve (it
gets a small stub or captcha page and, after repeated hits, a cumulative IP
ban). The browser loads the article page, solves the challenge, and the
downloader extracts the embedded `citation_pdf_url` and downloads that PDF.

Disable Sci-Hub entirely with `--no-scihub`. If you have a browser clearance
cookie, pass it with `--cookies`. Keep `--workers` modest; hammering Sci-Hub
gets the IP throttled regardless of the browser.

## arXiv

Module: `arxiv.py`. arXiv is fully open, so the candidate is simply
`https://arxiv.org/pdf/<id>` fetched over plain HTTP.

## URL

Module: `url.py`. For a raw URL the candidates are, in order:

1. the URL itself (direct `requests` download)
2. obvious PDF derivations: `*.html` to `*.pdf`, RFC editor links to the IETF
   `rfc<n>.txt.pdf` mirror, NASA NTRS citation pages to their download API
3. the original URL loaded in the browser, as a last resort for pages behind
   JavaScript or anti-bot walls

## The browser fallback

Any `requests` candidate that comes back as something other than a verified
document is retried automatically through the headless browser before moving to
the next candidate. This is why publisher and repository links that block
scripts still succeed. If no browser is available, these fall through and the
next candidate (or `not_found`) is used; non-browser sources are unaffected. See
[architecture](architecture.md) for the engine details.
