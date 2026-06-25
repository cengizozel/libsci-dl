"""Orchestration: identifier -> candidates -> downloaded file.

For each identifier we detect its type, ask the registered resolvers for
candidate download URLs (cheapest/legal sources first), then either return those
URLs (``url_only``) or download the first candidate that yields a verified file.
A manifest records progress so runs are resumable, and files moved away by other
tools are not re-fetched.
"""
from __future__ import annotations

import inspect
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, Optional

from .download import Downloader
from .identify import detect
from .manifest import Manifest
from .models import IdType, Result
from .resolvers import resolvers_for


def slugify(text: str, maxlen: int = 80) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return s[:maxlen] or "file"


def _filename_base(identifier: str, title: str) -> str:
    safe_id = slugify(identifier, 60)
    return f"{safe_id}__{slugify(title)}" if title else safe_id


def _call_resolver(resolver: Callable, identifier: str, title: str, http, opts: dict):
    params = inspect.signature(resolver).parameters
    kwargs = {}
    for key, val in {"title": title, "http": http, **opts}.items():
        if key in params:
            kwargs[key] = val
    return resolver(identifier, **kwargs)


class Engine:
    def __init__(self, out_dir: str = "downloads", manifest_path: Optional[str] = None,
                 email: str = "anonymous@example.com", url_only: bool = False,
                 size_cap: float = 80.0, scihub: bool = True,
                 downloader: Optional[Downloader] = None, verbose: bool = False,
                 on_result: Optional[Callable[[Result], None]] = None):
        self.out_dir = os.path.abspath(out_dir)
        os.makedirs(self.out_dir, exist_ok=True)
        self.manifest = Manifest(manifest_path or os.path.join(self.out_dir, "manifest.tsv"))
        self.email = email
        self.url_only = url_only
        self.size_cap = size_cap
        self.scihub = scihub
        self.verbose = verbose
        self.on_result = on_result
        self.downloader = downloader or Downloader(verbose=verbose)
        self._flush_lock = threading.Lock()
        self._since_flush = 0

    # -- resolution --------------------------------------------------------
    def resolve(self, identifier: str, id_type: IdType, title: str = "") -> list:
        opts = {"email": self.email, "size_cap": self.size_cap}
        http = self.downloader.session()
        candidates = []
        for resolver in resolvers_for(id_type):
            mod = getattr(resolver, "__module__", "")
            if not self.scihub and mod.endswith("doi_scihub"):
                continue
            try:
                candidates.extend(_call_resolver(resolver, identifier, title, http, opts))
            except Exception as exc:  # one bad resolver must not sink the rest
                if self.verbose:
                    print(f"    resolver {mod} failed: {exc}", flush=True)
        return candidates

    # -- one item ----------------------------------------------------------
    def process(self, raw: str, title: str = "") -> Result:
        id_type, identifier = detect(raw)
        res = Result(identifier=identifier, id_type=id_type, title=title)
        if id_type is IdType.UNKNOWN:
            res.status, res.error = "error", "unrecognized identifier"
            return res

        res.candidates = self.resolve(identifier, id_type, title)

        if self.url_only:
            res.status = "url_only" if res.candidates else "not_found"
            if res.candidates:
                res.source = res.candidates[0].source
            return res

        if not res.candidates:
            res.status = "not_found"
            return res

        base = os.path.join(self.out_dir, _filename_base(identifier, title))
        for cand in res.candidates:
            path = self.downloader.fetch(cand, base)
            if path:
                res.status, res.path, res.source = "ok", path, cand.source
                res.nbytes = os.path.getsize(path)
                return res
        res.status = "not_found"
        return res

    # -- batch -------------------------------------------------------------
    def run(self, items: Iterable, workers: int = 1,
            resume: bool = True) -> list[Result]:
        """``items`` is an iterable of identifier strings or (identifier, title) pairs."""
        pairs = [(it, "") if isinstance(it, str) else (it[0], it[1] or "") for it in items]
        results: list[Result] = []

        def handle(pair):
            raw, title = pair
            id_type, identifier = detect(raw)
            if resume and not self.url_only and self.manifest.is_done(identifier):
                if self.verbose:
                    print(f"  skip (done): {identifier}", flush=True)
                return None
            try:
                res = self.process(raw, title)
            except Exception as exc:  # one item must never sink the batch
                res = Result(identifier=identifier, id_type=id_type, title=title,
                             status="error", error=str(exc))
            self.manifest.record(res)
            with self._flush_lock:
                self._since_flush += 1
                if self._since_flush >= 5:
                    try:
                        self.manifest.flush()
                    except Exception:
                        pass
                    self._since_flush = 0
            if self.on_result:
                try:
                    self.on_result(res)
                except Exception:
                    pass
            return res

        if workers <= 1:
            for pair in pairs:
                r = handle(pair)
                if r:
                    results.append(r)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for r in pool.map(handle, pairs):
                    if r:
                        results.append(r)

        try:
            self.manifest.flush()
        except Exception:
            pass
        return results

    def close(self):
        self.manifest.flush()
        self.downloader.close()
