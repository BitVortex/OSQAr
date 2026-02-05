# My OSQAr Project (C)

This is a minimal OSQAr project scaffold.

## Quickstart

- Build docs (recommended):
  - Install deps (Poetry): `poetry install`
  - Build (OSQAr CLI, if installed): `osqar build-docs`
  - Build (fallback): `poetry run python -m sphinx -b html . _build/html`

- Build docs (no Poetry fallback):
  - Install docs deps: `python -m pip install -r requirements-docs.txt`
  - Build: `python -m sphinx -b html . _build/html`

- Generate placeholder evidence files for the docs:
  - `./build-and-test.sh`
