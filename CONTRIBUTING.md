# Contributing to dfstore

Thanks for taking the time to contribute! Here's everything you need to get started.

## Development setup

```bash
git clone https://github.com/tpazur/dfstore.git
cd dfstore
pip install -e ".[gui]" pytest pytest-cov ruff mypy
```

## Running tests

```bash
pytest                        # run all tests
pytest tests/test_save.py     # single file
pytest --cov=dfstore          # with coverage
```

## Linting

```bash
ruff check src tests          # lint
ruff check --fix src tests    # auto-fix
```

## Project structure

```
src/dfstore/
├── __init__.py      # public API (save, get, list, …)
├── store.py         # DFStore — core logic
├── models.py        # DFRecord, VersionRecord dataclasses
├── metadata.py      # JSON index read/write
├── storage.py       # parquet I/O and metadata extraction
├── diff.py          # shape/column diff between versions
├── cli.py           # Typer CLI
├── gui.py           # Flask web UI
├── exceptions.py    # DFStoreError, DFNotFoundError
└── templates/
    └── index.html   # Vue 3 single-page app
```

## Guidelines

- **Keep it focused.** dfstore is intentionally simple — avoid pulling in heavy dependencies.
- **Tests required.** New behaviour should come with tests. Bug fixes should include a test that would have caught the bug.
- **Public API changes** (anything in `__init__.py`) need a clear justification and a note in the PR description.
- **Commits** should be small and self-contained with a descriptive message.

## Submitting a pull request

1. Fork the repo and create a branch from `main`
2. Make your changes and ensure `pytest` and `ruff check` both pass
3. Open a PR — describe *what* changed and *why*

For larger changes, open an issue first to discuss the approach before writing code.
