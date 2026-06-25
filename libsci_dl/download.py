"""Fetching and verifying files.

Two engines:

* ``requests`` - fast plain HTTP, used for direct-PDF links (arXiv, Libgen,
  open-access repositories).
* Selenium (headless browser) - used when a site sits behind an anti-bot wall
  (Cloudflare / DDoS-Guard) or needs JavaScript, which ``requests`` cannot pass.
  This is the difference that makes Sci-Hub and PubMed Central work.

Every saved file is verified by magic bytes, so HTML error pages never get
stored as ``.pdf``.

Thread-safety: HTTP uses one ``requests.Session`` per thread; the single
headless browser is shared and guarded by a lock, so ``workers > 1`` parallelises
the (fast) HTTP sources while serialising the (slow) browser one.
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import threading
import time
from typing import Optional

import requests
import urllib3

from .models import Candidate, FetchMethod

DEFAULT_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36")

_MAGIC = {b"%PDF-": "pdf", b"AT&TFORM": "djvu", b"PK\x03\x04": "epub"}


def magic_ext(head: bytes) -> Optional[str]:
    for sig, ext in _MAGIC.items():
        if head.startswith(sig):
            return ext
    return None


def verify_file(path: str) -> Optional[str]:
    """Return the real extension from magic bytes, or None if not a known doc."""
    try:
        if os.path.getsize(path) < 1024:
            return None
        with open(path, "rb") as fh:
            return magic_ext(fh.read(8))
    except OSError:
        return None


class Downloader:
    def __init__(self, user_agent: str = DEFAULT_UA, read_timeout: int = 60,
                 file_deadline: int = 600, browser_wait: int = 40,
                 tmp_dir: Optional[str] = None, cookies: Optional[dict] = None,
                 insecure: bool = False, verbose: bool = False):
        self.ua = user_agent
        self.read_timeout = read_timeout
        self.file_deadline = file_deadline
        self.browser_wait = browser_wait
        self.cookies = cookies or {}
        self.insecure = insecure
        self.verbose = verbose
        self.tmp_dir = os.path.abspath(
            tmp_dir or os.path.expanduser("~/.cache/libsci-dl/parts"))
        os.makedirs(self.tmp_dir, exist_ok=True)
        if insecure:
            urllib3.disable_warnings()
        self._local = threading.local()
        self._sel_lock = threading.Lock()
        self._driver = None
        self._browser_failed = False  # set once if the browser can't start

    # -- per-thread HTTP session ------------------------------------------
    def session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"User-Agent": self.ua})
            s.verify = not self.insecure
            if self.cookies:
                s.cookies.update(self.cookies)
            self._local.session = s
        return s

    # -- requests engine ---------------------------------------------------
    def _requests_to(self, url: str, dest: str) -> Optional[str]:
        start, n, part = time.time(), 0, dest + ".part"
        try:
            with self.session().get(url, timeout=(15, self.read_timeout),
                                   stream=True, allow_redirects=True) as r:
                if r.status_code != 200:
                    return None
                with open(part, "wb") as fh:
                    for chunk in r.iter_content(65536):
                        if chunk:
                            fh.write(chunk)
                            n += len(chunk)
                        if time.time() - start > self.file_deadline:
                            raise TimeoutError
        except Exception:
            _silent_remove(part)
            return None
        ext = verify_file(part)
        if not ext:
            _silent_remove(part)
            return None
        os.replace(part, dest)
        return ext

    # -- selenium engine (single browser, lock-guarded) -------------------
    def _ensure_driver(self):
        if self._driver is not None:
            return self._driver
        if self._browser_failed:
            return None
        try:
            return self._start_driver()
        except Exception as exc:
            self._browser_failed = True
            if self.verbose:
                print(f"    browser unavailable, skipping browser sources: {exc}", flush=True)
            return None

    def _start_driver(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        opts = Options()
        for a in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-gpu", "--window-size=1280,1000"):
            opts.add_argument(a)
        opts.add_argument(f"--user-agent={self.ua}")
        opts.add_experimental_option("prefs", {
            "download.default_directory": self.tmp_dir,
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
        })
        d = webdriver.Chrome(options=opts)
        d.set_page_load_timeout(50)
        try:  # enable downloads in headless mode
            d.command_executor._commands["send_command"] = (
                "POST", "/session/$sessionId/chromium/send_command")
            d.execute("send_command", {"cmd": "Page.setDownloadBehavior",
                                       "params": {"behavior": "allow",
                                                  "downloadPath": self.tmp_dir}})
        except Exception:
            pass
        self._driver = d
        return d

    def _browser_download(self, url: str, dest: str) -> Optional[str]:
        with self._sel_lock:
            d = self._ensure_driver()
            if d is None:
                return None
            for f in glob.glob(os.path.join(self.tmp_dir, "*")):
                _silent_remove(f)
            try:
                d.get(url)  # navigating to a file triggers a download
            except Exception:
                pass        # the download may still proceed
            deadline = time.time() + self.browser_wait
            while time.time() < deadline:
                time.sleep(1.5)
                files = [f for f in glob.glob(os.path.join(self.tmp_dir, "*"))
                         if not f.endswith(".crdownload")]
                if files and os.path.getsize(files[0]) > 1024:
                    ext = verify_file(files[0])
                    if ext:
                        shutil.move(files[0], dest)
                        return ext
                    _silent_remove(files[0])
                    return None
            return None

    def _scihub_pdf_url(self, page_url: str) -> Optional[str]:
        with self._sel_lock:
            d = self._ensure_driver()
            if d is None:
                return None
            try:
                d.get(page_url)
            except Exception:
                return None
            time.sleep(6)
            html = d.page_source
        m = (re.search(r'citation_pdf_url"\s+content="([^"]+)"', html)
             or re.search(r'(?:embed|iframe)[^>]+src="([^"]+\.pdf[^"]*)"', html, re.I))
        if not m:
            return None
        u = m.group(1)
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            base = re.match(r"https?://[^/]+", page_url)
            return (base.group(0) if base else "") + u
        return u

    # -- public ------------------------------------------------------------
    def fetch(self, cand: Candidate, dest_no_ext: str) -> Optional[str]:
        """Download a candidate. Returns the saved path, or None on failure.

        The extension is decided by the file's magic bytes, not the URL.
        """
        if self.verbose:
            print(f"    try {cand.method.value} <{cand.source}>: {cand.url[:90]}", flush=True)
        tmp = dest_no_ext + ".download"
        ext = None
        if cand.method is FetchMethod.REQUESTS:
            ext = self._requests_to(cand.url, tmp)
            if ext is None:  # link may sit behind anti-bot/JS, so try the browser
                ext = self._browser_download(cand.url, tmp)
        elif cand.method is FetchMethod.SELENIUM:
            ext = self._browser_download(cand.url, tmp)
        elif cand.method is FetchMethod.SELENIUM_SCIHUB:
            pdf = self._scihub_pdf_url(cand.url)
            if pdf:
                ext = self._requests_to(pdf, tmp) or self._browser_download(pdf, tmp)
        if not ext:
            return None
        final = f"{dest_no_ext}.{ext}"
        os.replace(tmp, final)
        return final

    def close(self):
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None


def _silent_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
