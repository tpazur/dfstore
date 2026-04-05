# Commands

## git-commit
Commit only the currently staged files — do not stage anything extra.
Write a brief, lowercase commit message describing what changed. Do not mention Claude or AI in the message.

## git-release
1. Determine the new version by inspecting the current version in `pyproject.toml` and the git log since the last tag.
2. Update the `version` field in `pyproject.toml`.
3. Update `__version__` in `src/dfstore/__init__.py` — replace the fallback string `"0.0.0"` with the new version so it is hardcoded alongside the importlib lookup.
4. Create or update `CHANGELOG.md`: prepend a new section for the new version listing the most important changes since the previous version tag (use `git log` to derive them). Keep entries concise.
5. Stage `pyproject.toml`, `src/dfstore/__init__.py`, and `CHANGELOG.md`, then commit with message `release vX.Y.Z`.
6. Create an annotated git tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`.
7. Push the commit and tag: `git push && git push --tags`.
8. Create a GitHub release with `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file CHANGELOG.md` (use only the section for this version as the notes).
