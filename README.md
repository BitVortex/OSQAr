(This project README was intentionally left minimal for the example.)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OSQAr

Open Safety Qualification Architecture (OSQAr) — a Sphinx + sphinx-needs
boilerplate for requirements traceability, architecture diagrams, and
test traceability suitable for safety-related documentation and examples.

For license terms see the `LICENSE` file (Apache License 2.0).


The [example](https://bitvortex.github.io/OSQAr/example/) is built and deployed automatically on pushes to `main` (via `.github/workflows/gh-pages.yml`) from the sources in the `examples/hello_world` directtory.

To view the example locally:

```bash
# from the repository root
pip install Sphinx sphinx-press-theme sphinx-needs sphinxcontrib-plantuml
sphinx-build -b html examples/hello_world examples/hello_world/_build/html
open examples/hello_world/_build/html/index.html
```
