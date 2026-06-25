"""Offline tests for identifier detection (no network)."""
from libsci_dl.identify import detect
from libsci_dl.models import IdType


def test_doi():
    assert detect("10.1038/323533a0") == (IdType.DOI, "10.1038/323533a0")
    assert detect("doi:10.1145/50202.50214")[0] is IdType.DOI
    assert detect("https://doi.org/10.1038/323533a0") == (IdType.DOI, "10.1038/323533a0")


def test_arxiv():
    assert detect("1706.03762") == (IdType.ARXIV, "1706.03762")
    assert detect("2301.01234v2") == (IdType.ARXIV, "2301.01234v2")
    assert detect("arXiv:1506.02640")[0] is IdType.ARXIV
    assert detect("hep-th/9901001")[0] is IdType.ARXIV
    assert detect("cond-mat.stat-mech/0123456")[0] is IdType.ARXIV  # hyphenated subclass
    assert detect("https://arxiv.org/abs/1706.03762") == (IdType.ARXIV, "1706.03762")
    assert detect("https://arxiv.org/pdf/1706.03762.pdf") == (IdType.ARXIV, "1706.03762")


def test_isbn():
    assert detect("9780471433347") == (IdType.ISBN, "9780471433347")
    assert detect("978-0-471-43334-7") == (IdType.ISBN, "9780471433347")
    assert detect("0306406152")[0] is IdType.ISBN          # ISBN-10
    assert detect("080442957X")[0] is IdType.ISBN          # ISBN-10 with X check digit


def test_url():
    assert detect("https://bitcoin.org/bitcoin.pdf") == (IdType.URL, "https://bitcoin.org/bitcoin.pdf")


def test_unknown():
    assert detect("")[0] is IdType.UNKNOWN
    assert detect("not an identifier")[0] is IdType.UNKNOWN
