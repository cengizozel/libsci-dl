# libsci-dl documentation

Detailed documentation for libsci-dl. For a quick overview and install steps,
see the top-level [README](../README.md).

- [CLI reference](cli.md): every flag, the input file format, url-only mode,
  exit codes, and examples.
- [Sources](sources.md): how each source (Libgen, Unpaywall, PubMed Central,
  Sci-Hub, arXiv, URL) is resolved and downloaded, including mirrors and quirks.
- [Architecture](architecture.md): the module map, the resolve-then-download
  flow, the manifest, the concurrency model, and file verification.
- [Library API](library.md): using `Engine`, `Downloader`, `Manifest`, and the
  data types from Python.
- [Extending](extending.md): add a new source by writing a resolver.
- [Troubleshooting](troubleshooting.md): chromedriver setup, rate limits,
  cookies, TLS, and resume behavior.
