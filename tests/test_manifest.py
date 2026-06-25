"""Offline tests for the resumable manifest."""
import os
import tempfile

from libsci_dl.manifest import Manifest
from libsci_dl.models import IdType, Result


def test_roundtrip_and_resume():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "manifest.tsv")
        m = Manifest(path)
        m.record(Result(identifier="10.1/x", id_type=IdType.DOI, title="A",
                        status="ok", path="/tmp/a.pdf", nbytes=10))
        m.flush()
        # reload and confirm persisted state
        m2 = Manifest(path)
        assert m2.is_done("10.1/x")
        assert m2.status("missing") is None


def test_tab_in_title_does_not_corrupt():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "manifest.tsv")
        m = Manifest(path)
        m.record(Result(identifier="x", id_type=IdType.ISBN,
                        title="Bad\ttitle\twith\ttabs", status="ok"))
        m.flush()
        # every data line must have exactly the right number of columns
        with open(path) as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                assert len(line.rstrip("\n").split("\t")) == 7
        assert Manifest(path).is_done("x")
