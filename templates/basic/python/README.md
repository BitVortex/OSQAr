# My OSQAr Project (Python)

This is a minimal OSQAr project scaffold.

## Quickstart

- Install deps (Poetry): https://python-poetry.org/
- Build docs:

  ```bash
  poetry install
  # If you have the OSQAr CLI installed on PATH:
  osqar build-docs

  # Fallback:
  poetry run python -m sphinx -b html . _build/html
  ```

- Generate placeholder evidence files for the docs:

  ```bash
  ./build-and-test.sh
  ```
