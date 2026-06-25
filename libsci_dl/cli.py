"""Command-line interface for libsci-dl."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from . import __version__
from .core import Engine
from .download import Downloader
from .identify import detect
from .models import Result


def _read_items(args) -> list[tuple[str, str]]:
    """Collect (identifier, optional-title) pairs from positionals and --file.

    File lines may be a bare identifier or tab-separated; the first field is the
    identifier and the last field (if more than one) is treated as the title.
    Lines starting with ``#`` and blank lines are ignored.
    """
    items: list[tuple[str, str]] = []
    for ident in args.identifiers:
        items.append((ident, ""))
    for path in args.file or []:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = line.split("\t")
                ident = parts[0].strip()
                title = parts[-1].strip() if len(parts) > 1 else ""
                if ident:
                    items.append((ident, title))
    return items


def _load_cookies(path: Optional[str]) -> dict:
    if not path:
        return {}
    cookies: dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):  # JSON export
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("cookies", [])
        for c in rows:
            if c.get("name"):
                cookies[c["name"]] = c.get("value", "")
    else:  # Netscape cookies.txt
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            f = line.split("\t")
            if len(f) >= 7:
                cookies[f[5]] = f[6]
    return cookies


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="libsci-dl",
        description="Resolve and download books/papers by identifier "
                    "(ISBN via Libgen; DOI via open access, PMC, Sci-Hub; arXiv; URL).")
    p.add_argument("identifiers", nargs="*",
                   help="one or more identifiers (ISBN / DOI / arXiv id / URL)")
    p.add_argument("-f", "--file", action="append", metavar="PATH",
                   help="file with one identifier per line (repeatable)")
    p.add_argument("-o", "--out", default="downloads", metavar="DIR",
                   help="output directory (default: ./downloads)")
    p.add_argument("-u", "--url-only", action="store_true",
                   help="only resolve download URLs, do not download")
    p.add_argument("-w", "--workers", type=int, default=1, metavar="N",
                   help="parallel workers (HTTP sources run in parallel; the "
                        "browser is serialised). Default 1")
    p.add_argument("--email", default="anonymous@example.com",
                   help="contact email for Unpaywall/NCBI APIs (be polite)")
    p.add_argument("--no-scihub", action="store_true",
                   help="disable the Sci-Hub fallback (use only legal sources)")
    p.add_argument("--size-cap", type=float, default=80.0, metavar="MB",
                   help="prefer book editions at or below this size (default 80)")
    p.add_argument("--manifest", metavar="PATH",
                   help="manifest path (default: <out>/manifest.tsv)")
    p.add_argument("--no-resume", action="store_true",
                   help="re-attempt identifiers already marked done")
    p.add_argument("--cookies", metavar="PATH",
                   help="cookies.txt or JSON cookie export (e.g. for Sci-Hub)")
    p.add_argument("--insecure", action="store_true",
                   help="disable TLS certificate verification (last resort for "
                        "mirrors with broken certs)")
    p.add_argument("--browser-wait", type=int, default=40, metavar="SEC",
                   help="seconds to wait for a browser download (default 40)")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("-V", "--version", action="version",
                   version=f"libsci-dl {__version__}")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    items = _read_items(args)
    if not items:
        build_parser().print_help(sys.stderr)
        print("\nerror: no identifiers given", file=sys.stderr)
        return 2

    downloader = Downloader(cookies=_load_cookies(args.cookies),
                            browser_wait=args.browser_wait,
                            insecure=args.insecure, verbose=args.verbose)

    counts = {"ok": 0, "not_found": 0, "error": 0, "url_only": 0}

    def report(res: Result):
        counts[res.status] = counts.get(res.status, 0) + 1
        if args.url_only:
            url = res.candidates[0].url if res.candidates else "NONE"
            print(f"{res.identifier}\t{res.status}\t{url}")
        else:
            tag = {"ok": "OK ", "not_found": "MISS", "error": "ERR "}.get(res.status, res.status)
            extra = f" from {res.source}" if res.status == "ok" else (f" ({res.error})" if res.error else "")
            done = counts["ok"] + counts["not_found"] + counts["error"]
            print(f"[{done}] {tag} {res.identifier}{extra}", flush=True)

    engine = Engine(out_dir=args.out, manifest_path=args.manifest, email=args.email,
                    url_only=args.url_only, size_cap=args.size_cap,
                    scihub=not args.no_scihub, downloader=downloader,
                    verbose=args.verbose, on_result=report)

    try:
        results = engine.run(items, workers=args.workers, resume=not args.no_resume)
    finally:
        engine.close()

    if args.url_only:
        url_file = os.path.join(os.path.abspath(args.out), "urls.tsv")
        os.makedirs(os.path.dirname(url_file), exist_ok=True)
        with open(url_file, "w", encoding="utf-8") as fh:
            fh.write("# identifier\ttype\tstatus\tsource\turls\ttitle\n")
            for r in results:
                urls = " ".join(dict.fromkeys(c.url for c in r.candidates)) or "NONE"
                fh.write(f"{r.identifier}\t{r.id_type.value}\t{r.status}\t{r.source}\t{urls}\t{r.title}\n")
        print(f"\nWrote {len(results)} rows to {url_file}", file=sys.stderr)

    print(f"\nDone. " + "  ".join(f"{k}={v}" for k, v in counts.items() if v),
          file=sys.stderr)
    return 0 if counts.get("ok") or args.url_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
