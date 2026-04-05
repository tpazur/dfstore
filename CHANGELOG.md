# Changelog

## v0.1.0

Initial release.

- Save, retrieve, list, search, and delete pandas and polars DataFrames
- Versioning with full version history per DataFrame
- Rich metadata: descriptions, tags, notes, diff tracking (row/column delta)
- Soft delete with restore support
- CLI (`dfstore`) powered by Typer
- Web UI via Flask
- Zero infrastructure — plain files stored in `~/.dfstore`
- `DFSTORE_PATH` environment variable for custom store location
- Branch protection and CODEOWNERS configured for the repo
- CI matrix across Python 3.10–3.14 × pandas 2.0/2.2 × polars 0.20/1.0/1.20 via tox and GitHub Actions
