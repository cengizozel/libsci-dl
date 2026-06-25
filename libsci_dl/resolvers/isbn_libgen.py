"""ISBN -> Library Genesis.

Flow that works in practice:
  GET {mirror}/index.php?req=<ISBN>      -> results table (md5 per row)
  GET {mirror}/ads.php?md5=<MD5>         -> page containing get.php?md5=...&key=...
  the get.php link is the direct download.

We prefer the *smallest* valid edition (pdf > epub > djvu, <= size cap, then
smallest file). Bandwidth is the bottleneck, so a small text PDF beats a 150 MB
scan of the same book and lets far more books finish.
"""
from __future__ import annotations

import re

from ..models import Candidate, FetchMethod

MIRRORS = ["https://libgen.li", "https://libgen.vg"]
FMT_RANK = {"pdf": 4, "epub": 3, "djvu": 2, "mobi": 1, "azw3": 1}
_MD5_RE = re.compile(r"md5=([A-Fa-f0-9]{32})")
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_GET_RE = re.compile(r'href="(get\.php\?md5=[A-Fa-f0-9]{32}&key=\w+)"')


def _size_mb(text: str) -> float:
    m = re.search(r"([\d.]+)\s*(K|M|G)B", text or "", re.I)
    if not m:
        return 999.0
    val, unit = float(m.group(1)), m.group(2).upper()
    return val / 1024 if unit == "K" else (val if unit == "M" else val * 1024)


def _strip(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).strip().replace("\n", " ")


def _parse_rows(html: str) -> list[dict]:
    rows = []
    for row in _ROW_RE.findall(html):
        md5 = _MD5_RE.search(row)
        if not md5:
            continue
        cells = [_strip(c) for c in _CELL_RE.findall(row)]
        if len(cells) < 8:
            continue
        rows.append({
            "md5": md5.group(1),
            "title": cells[0],
            "lang": cells[4],
            "size_mb": _size_mb(cells[6]),
            "ext": cells[7].lower(),
        })
    return rows


def _pick(rows: list[dict], size_cap: float) -> dict:
    # under-cap-ness outranks format, so a small EPUB/DjVu beats a giant PDF scan;
    # among under-cap files, prefer format (PDF best), then English, then smallest.
    return max(rows, key=lambda e: (
        1 if e["size_mb"] <= size_cap else 0,
        FMT_RANK.get(e["ext"], 0),
        1 if e["lang"].lower().startswith("eng") else 0,
        -e["size_mb"],
    ))


def resolve(identifier: str, title: str = "", http=None, size_cap: float = 80.0) -> list[Candidate]:
    if http is None:
        import requests
        http = requests.Session()
        http.verify = False
    isbn = identifier.strip()
    for mirror in MIRRORS:
        try:
            r = http.get(f"{mirror}/index.php?req={isbn}", timeout=(15, 25))
        except Exception:
            continue
        if r.status_code != 200 or "md5=" not in r.text:
            continue
        rows = _parse_rows(r.text)
        if not rows:
            continue
        best = _pick(rows, size_cap)
        try:
            ads = http.get(f"{mirror}/ads.php?md5={best['md5']}", timeout=(15, 25)).text
        except Exception:
            continue
        m = _GET_RE.search(ads)
        if not m:
            continue
        host = mirror.split("//", 1)[-1]
        return [Candidate(
            url=f"{mirror}/{m.group(1)}",
            source=f"libgen:{host}",
            method=FetchMethod.REQUESTS,
            ext=best["ext"] if best["ext"] in FMT_RANK else "pdf",
            note=f"{best['ext']}, {best['size_mb']:.1f}MB, {best['lang']}",
        )]
    return []
