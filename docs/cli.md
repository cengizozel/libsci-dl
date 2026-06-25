# CLI reference

```
libsci-dl [identifiers ...] [options]
```

Run `libsci-dl --help` for the same list. The command is installed by
`pip install -e .`; you can also run it as `python -m libsci_dl`.

## Inputs

Identifiers can be given as positional arguments, from one or more files with
`--file`, or both. Each identifier is auto-detected as one of:

- ISBN (10 or 13 digits, hyphens allowed; `978`/`979` prefix for ISBN-13)
- DOI (`10.xxxx/...`, a `doi:` prefix, or a `doi.org/...` URL)
- arXiv id (`2301.01234`, `2301.01234v2`, or legacy `hep-th/9901001`; an
  `arxiv.org/abs|pdf/...` URL is accepted too)
- URL (anything starting with `http://`, `https://`, or `www.`)

Anything else is reported as `error: unrecognized identifier`.

### File format

One identifier per line. A line may be a bare identifier, or tab-separated
where the **first** field is the identifier and the **last** field is an
optional title used to name the saved file. Blank lines and lines beginning
with `#` are ignored.

```
9780471433347	isbn	Abstract Algebra - Dummit & Foote
10.1038/323533a0	doi	Learning representations by back-propagating errors
1706.03762
https://bitcoin.org/bitcoin.pdf
```

Because only the first and last tab fields are used, the three-column
`identifier <tab> type <tab> title` lists produced by `cut`-style pipelines work
without changes.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `-f, --file PATH` | - | File of identifiers, one per line. Repeatable. |
| `-o, --out DIR` | `downloads` | Output directory. Created if missing. |
| `-u, --url-only` | off | Resolve links only; download nothing. Writes `<out>/urls.tsv`. |
| `-w, --workers N` | `1` | Parallel workers. HTTP sources run in parallel; the single browser is serialised behind a lock. |
| `--email ADDR` | `anonymous@example.com` | Contact email sent to the Unpaywall and NCBI APIs. Set a real address to be polite. |
| `--no-scihub` | off | Disable the Sci-Hub fallback (open-access sources only). |
| `--size-cap MB` | `80` | Prefer book editions at or below this size. See [sources](sources.md). |
| `--manifest PATH` | `<out>/manifest.tsv` | Where the resumable manifest is written. |
| `--no-resume` | off | Re-attempt identifiers already marked `ok` in the manifest. |
| `--cookies PATH` | - | A `cookies.txt` (Netscape) or JSON cookie export, applied to HTTP requests. Useful for a Sci-Hub clearance cookie. |
| `--browser-wait SEC` | `40` | Seconds to wait for a browser-driven download to finish. |
| `--insecure` | off | Disable TLS certificate verification. Last resort for a mirror with a broken certificate. |
| `-v, --verbose` | off | Print each candidate attempt. |
| `-V, --version` | - | Print version and exit. |

## Output

### Download mode (default)

Files are written to `--out` named `<identifier>__<title-slug>.<ext>`, where the
extension comes from the file's magic bytes, not the URL. Progress is printed
per item:

```
[1] OK  9780471433347 from libgen:libgen.li
[2] MISS 10.9999/nope.123
[3] OK  1706.03762 from arxiv
```

A summary line is printed at the end (`Done. ok=2  not_found=1`).

### url-only mode

Nothing is downloaded. A tab-separated file `<out>/urls.tsv` is written with the
columns `identifier  type  status  source  urls  title`, where `urls` is a
space-separated, de-duplicated list of candidate links in priority order. The
same rows are also printed to stdout as `identifier <tab> status <tab> first-url`.

## Exit codes

- `0` - at least one item was downloaded, or url-only mode ran.
- `1` - nothing was downloaded.
- `2` - no identifiers were given.

## Examples

```bash
# A single book
libsci-dl 9780262033848 --out books/

# A mixed batch, 4 workers, real email for the APIs
libsci-dl --file wanted.txt --out lib/ --workers 4 --email you@example.com

# Only legal open-access copies of a DOI list
libsci-dl --file dois.txt --no-scihub

# Just collect links for review
libsci-dl --file wanted.txt --url-only --out review/

# Resume a previous run (default); force a full re-run with --no-resume
libsci-dl --file wanted.txt --out lib/
libsci-dl --file wanted.txt --out lib/ --no-resume

# Provide a Sci-Hub clearance cookie exported from your browser
libsci-dl --file dois.txt --cookies scihub_cookies.txt
```
