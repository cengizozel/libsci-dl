# libsci-dl

Resolve and download books and papers from a list of identifiers (ISBN, DOI, arXiv ID, or URL). Books come from Library Genesis; papers come from open access, PubMed Central, and Sci-Hub; arXiv and direct URLs are handled too.

Give it one identifier or a file with thousands, one per line. It detects what each one is, finds a download link, verifies the file is a real document, and saves it, resuming where it left off if interrupted.

```bash
libsci-dl 9780471433347
libsci-dl 10.1038/323533a0 1706.03762
libsci-dl --file ids.txt --out books/ --workers 4
libsci-dl --file ids.txt --url-only            # collect links, download nothing
```

## What makes it work

- **Anti-bot sources work.** Sci-Hub (DDoS-Guard) and PubMed Central serve a JavaScript/captcha page that plain HTTP cannot pass. libsci-dl drives a real headless browser for those, which solves the challenge like your browser would, and falls back to it automatically whenever a plain download returns HTML instead of a file.
- **It prefers the smallest valid edition** of a book (PDF over EPUB over DjVu, under a size cap, then smallest file). Bandwidth is the bottleneck, so a 9 MB text PDF beats a 150 MB scan and lets far more items finish.
- **Every saved file is verified by magic bytes** (PDF, DjVu, EPUB), so HTML error pages never get stored as `.pdf`.
- **Resumable.** A manifest records what succeeded, so re-running skips finished items and files you move elsewhere are not re-downloaded.

## Sources by identifier type

| Identifier | Sources, in order |
|-----------|--------------------|
| ISBN | Library Genesis (`libgen.li`, `libgen.vg`) |
| DOI | Unpaywall (open access), then PubMed Central, then Sci-Hub |
| arXiv | arxiv.org |
| URL | the URL directly, plus `.pdf` derivations, then a browser fallback |

Legal open-access sources are always tried before Sci-Hub. Use `--no-scihub` to stay open-access only.

## Install

Requires Python 3.9+. The browser-based sources also need Chrome or Chromium plus chromedriver on your PATH (Selenium 4 can usually manage the driver itself). Without a browser, ISBN, arXiv, and direct-PDF sources still work.

```bash
git clone https://github.com/cengizozel/libsci-dl
cd libsci-dl
pip install -e .
```

## Basic usage

```bash
libsci-dl <identifier> [<identifier> ...]      # one or more, any type
libsci-dl --file ids.txt --out downloads/      # a file of identifiers
libsci-dl --file ids.txt --url-only            # only resolve links
libsci-dl 10.1145/50202.50214 --no-scihub      # open access only
```

Input files have one identifier per line. A line may be bare, or tab-separated where the first field is the identifier and the last field is an optional title used to name the file. Blank lines and lines starting with `#` are ignored, so `cut -f1`-style lists work as-is. See [`examples/sample_ids.txt`](examples/sample_ids.txt).

## Documentation

Detailed docs live in [`docs/`](docs/):

- [CLI reference](docs/cli.md) - every flag, input formats, url-only mode, exit codes, examples.
- [Sources](docs/sources.md) - how each source is resolved and downloaded, mirrors, and quirks.
- [Architecture](docs/architecture.md) - module map, the resolve-then-download flow, manifest, concurrency, verification.
- [Library API](docs/library.md) - using `Engine`, `Downloader`, `Manifest`, and the data types from Python.
- [Extending](docs/extending.md) - add a new source by writing a resolver.
- [Troubleshooting](docs/troubleshooting.md) - chromedriver, rate limits, cookies, TLS.

## Legal

This tool automates access to third-party services, some of which host copyrighted material without permission; downloading such material may be illegal where you live. It is intended for legitimate uses: open-access works, material you are licensed to access, and text and data mining where permitted. You are responsible for how you use it and for complying with the law and each service's terms. The author hosts no content and does not endorse infringement.

## License

MIT, see [LICENSE](LICENSE).
