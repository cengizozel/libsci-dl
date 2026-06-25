# libsci-dl

Resolve and download books and papers from a list of identifiers — **ISBN, DOI, arXiv ID, or URL** — pulling from **Library Genesis** (books), **open access → PubMed Central → Sci-Hub** (papers), and **arXiv**.

Give it one identifier or a file with thousands, one per line. It figures out what each one is, finds a download link, verifies the file is a real document, and saves it — resuming where it left off if interrupted.

```bash
libsci-dl 9780471433347
libsci-dl 10.1038/323533a0 1706.03762
libsci-dl --file ids.txt --out books/ --workers 4
libsci-dl --file ids.txt --url-only            # just collect links, download nothing
```

## Why it exists

Most identifier-to-PDF tools break on two things: they pick giant scanned editions that never finish, and they fall over the moment a source puts up an anti-bot wall. libsci-dl handles both:

- **Anti-bot sources work.** Sci-Hub (DDoS-Guard) and PubMed Central serve a JavaScript/captcha interstitial that plain HTTP can't pass. libsci-dl uses a real headless browser for those sources, which solves the challenge exactly like your browser would — and falls back to it automatically whenever a plain download returns an HTML page instead of a file.
- **It prefers the *smallest* valid edition** of a book (PDF > EPUB > DjVu, under a size cap, then smallest file). Bandwidth is the bottleneck, so a 9 MB text PDF beats a 150 MB scan of the same book and lets far more items finish.
- **Every saved file is verified by magic bytes** (`%PDF`, DjVu, EPUB), so HTML error pages never get stored as `.pdf`.
- **Resumable.** A manifest records what succeeded; re-running skips finished items, and files you move/upload elsewhere aren't re-downloaded.

## Sources by identifier type

| Identifier | Sources tried, in order |
|-----------|--------------------------|
| **ISBN** | Library Genesis (`libgen.li`, `libgen.vg`) |
| **DOI** | Unpaywall (open access) → PubMed Central → Sci-Hub |
| **arXiv** | arxiv.org |
| **URL** | the URL directly, plus obvious `.pdf` derivations (JMLR, RFC, NASA NTRS), then a browser fallback |

Legal open-access sources are always tried before Sci-Hub. Use `--no-scihub` to stay open-access-only.

## Install

Requires Python 3.9+ and, for the browser-based sources, **Chrome/Chromium + chromedriver** on your PATH (Selenium 4 can usually auto-manage the driver).

```bash
git clone https://github.com/cengizozel/libsci-dl
cd libsci-dl
pip install -e .          # installs the `libsci-dl` command
# or, deps only:  pip install -r requirements.txt   # then run: python -m libsci_dl ...
```

## Usage

```
libsci-dl [identifiers...] [options]

  -f, --file PATH       file with one identifier per line (repeatable)
  -o, --out DIR         output directory (default: ./downloads)
  -u, --url-only        only resolve URLs, don't download (writes <out>/urls.tsv)
  -w, --workers N       parallel workers; HTTP sources run in parallel, the
                        browser is serialised (default: 1)
      --email ADDR      contact email for Unpaywall/NCBI APIs
      --no-scihub       disable the Sci-Hub fallback (open access only)
      --size-cap MB     prefer book editions at or below this size (default: 80)
      --manifest PATH   manifest location (default: <out>/manifest.tsv)
      --no-resume       re-attempt identifiers already marked done
      --cookies PATH    cookies.txt or JSON export (e.g. a Sci-Hub clearance cookie)
      --browser-wait S  seconds to wait for a browser download (default: 40)
      --insecure        disable TLS verification (last resort for broken certs)
  -v, --verbose
  -V, --version
```

### Input file format

One identifier per line. Lines may be bare, or tab-separated where the **first** field is the identifier and the **last** field is an optional title (used to name the file). `#` comments and blank lines are ignored — so the `cut -f1`-style lists you already have work as-is:

```
9780471433347	isbn	Abstract Algebra - Dummit & Foote
10.1038/323533a0	doi	Learning representations by back-propagating errors
1706.03762	arxiv	Attention Is All You Need
https://bitcoin.org/bitcoin.pdf
```

See [`examples/sample_ids.txt`](examples/sample_ids.txt).

### url-only mode

`--url-only` resolves links without downloading and writes `<out>/urls.tsv`
(`identifier · type · status · source · urls · title`). Handy for review, or to
feed links into another tool.

## Library use

```python
from libsci_dl import Engine

engine = Engine(out_dir="downloads", email="you@example.com")
results = engine.run(["9780471433347", "10.1038/323533a0", "1706.03762"])
for r in results:
    print(r.status, r.identifier, r.path or r.error)
engine.close()
```

Add a source by writing a resolver `resolve(identifier, title="", http=None) -> list[Candidate]`
and registering it in `libsci_dl/resolvers/__init__.py`.

## How it works

```
identifier ──▶ detect type ──▶ resolvers (per type) ──▶ candidate URLs
                                                              │
                                            download each in order, first that
                                            yields a magic-byte-verified file wins
                                                              │
                          requests (fast)  ◀──┴──▶  headless browser (anti-bot / JS)
```

- `identify.py` — detect ISBN / DOI / arXiv / URL and normalize.
- `resolvers/` — one module per source; each returns candidate download URLs.
- `download.py` — `requests` + Selenium engines, magic-byte verification, per-file deadlines.
- `core.py` — orchestration, concurrency, resumable manifest.
- `cli.py` — the command line.

## Notes & limitations

- The browser-based sources need Chromium + chromedriver; without them, ISBN-via-Libgen, arXiv, and direct PDF URLs still work, and DOI falls back to whatever open-access direct PDFs exist.
- Sci-Hub mirrors and rate limits change; hammering them gets your IP throttled. Keep `--workers` modest, and pass a browser clearance cookie via `--cookies` if needed.
- Coverage is not 100%: very new papers may not be on Sci-Hub, and some books aren't on Libgen.
- URL-type inputs are fetched as-is — only pass URLs you trust (no SSRF guard is applied).

## Legal

This tool automates access to third-party services. Some of those services host
copyrighted material without the rightsholder's permission, and downloading such
material may be illegal in your jurisdiction. It is provided for legitimate uses
— retrieving open-access works, material you are licensed to access, and text/
data-mining where permitted. **You are responsible for how you use it and for
complying with the law and each service's terms.** The author does not host any
content and does not endorse infringement.

## License

MIT — see [LICENSE](LICENSE).
