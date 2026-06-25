"""A small resumable ledger.

The manifest is the source of truth for what has been downloaded, so a run can
resume after a crash and so that files being moved/uploaded elsewhere do not
trigger re-downloads.
"""
from __future__ import annotations

import os
import threading

COLUMNS = ["identifier", "type", "status", "source", "path", "bytes", "title"]


class Manifest:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._rows: dict[str, dict] = {}
        if os.path.exists(path):
            self._load()

    def _load(self) -> None:
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < len(COLUMNS):
                    continue
                row = dict(zip(COLUMNS, parts))
                self._rows[row["identifier"]] = row

    def status(self, identifier: str) -> str | None:
        row = self._rows.get(identifier)
        return row["status"] if row else None

    def is_done(self, identifier: str) -> bool:
        """Done means OK (downloaded) - trusted even if the file was moved away."""
        return self.status(identifier) == "ok"

    def record(self, result) -> None:
        with self._lock:
            self._rows[result.identifier] = result.as_row()

    def flush(self) -> None:
        with self._lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write("# " + "\t".join(COLUMNS) + "\n")
                for row in self._rows.values():
                    fh.write("\t".join(
                        str(row.get(c, "")).replace("\t", " ").replace("\n", " ")
                        for c in COLUMNS) + "\n")
            os.replace(tmp, self.path)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in self._rows.values():
            out[row["status"]] = out.get(row["status"], 0) + 1
        return out
