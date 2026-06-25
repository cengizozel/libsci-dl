"""Offline tests for resolver construction (no network)."""
from libsci_dl.models import FetchMethod
from libsci_dl.resolvers import arxiv, url
from libsci_dl.resolvers.isbn_libgen import _parse_rows, _pick, _size_mb


def test_arxiv_candidate():
    cands = arxiv.resolve("1706.03762")
    assert cands and cands[0].url == "https://arxiv.org/pdf/1706.03762"
    assert cands[0].method is FetchMethod.REQUESTS


def test_url_derivations():
    cands = url.resolve("https://jmlr.org/papers/v3/bengio03a.html")
    urls = [c.url for c in cands]
    assert "https://jmlr.org/papers/v3/bengio03a.pdf" in urls
    # original URL kept and a browser fallback added
    assert any(c.method is FetchMethod.SELENIUM for c in cands)


def test_rfc_derivation():
    cands = url.resolve("https://www.rfc-editor.org/rfc/rfc1771")
    urls = [c.url for c in cands]
    assert "https://www.ietf.org/rfc/rfc1771.txt.pdf" in urls


def test_pick_small_noncap_beats_giant_pdf():
    rows = [
        {"md5": "big", "title": "x", "lang": "English", "size_mb": 200.0, "ext": "pdf"},
        {"md5": "small", "title": "x", "lang": "English", "size_mb": 3.0, "ext": "epub"},
    ]
    # the only under-cap file is the epub; it should win over a 200MB PDF scan
    assert _pick(rows, size_cap=80.0)["md5"] == "small"


def test_size_mb():
    assert _size_mb("8 MB") == 8.0
    assert abs(_size_mb("512 KB") - 0.5) < 1e-6
    assert _size_mb("1 GB") == 1024.0
    assert _size_mb("") == 999.0


def test_pick_prefers_small_pdf():
    rows = [
        {"md5": "a", "title": "x", "lang": "English", "size_mb": 150.0, "ext": "pdf"},
        {"md5": "b", "title": "x", "lang": "English", "size_mb": 9.0, "ext": "pdf"},
        {"md5": "c", "title": "x", "lang": "English", "size_mb": 2.0, "ext": "djvu"},
    ]
    best = _pick(rows, size_cap=80.0)
    assert best["md5"] == "b"  # pdf, under cap, smallest


def test_parse_rows_basic():
    html = (
        "<tr><td>Title</td><td>Author</td><td>Pub</td><td>2004</td>"
        "<td>English</td><td>945</td><td>8 MB</td><td>pdf</td>"
        "<td><a href='ads.php?md5=" + "a" * 32 + "'>x</a></td></tr>"
    )
    rows = _parse_rows(html)
    assert len(rows) == 1 and rows[0]["ext"] == "pdf" and rows[0]["size_mb"] == 8.0
