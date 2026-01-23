(This project README was intentionally left minimal for the example.)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# OSQAr

Open Safety Qualification Architecture (OSQAr) — a Sphinx + sphinx-needs
boilerplate for requirements traceability, architecture diagrams, and
test traceability suitable for safety-related documentation and examples.

For license terms see the `LICENSE` file (Apache License 2.0).

Live example:

- **Hosted (GitHub Pages)**: https://bitvortex.github.io/OSQAr/ — the example
	documentation at `examples/hello_world/_build/html` is built and deployed
	automatically on pushes to `main` (via `.github/workflows/gh-pages.yml`).

To view the example locally:

```bash
# from the repository root
pip install Sphinx sphinx-press-theme sphinx-needs sphinxcontrib-plantuml
sphinx-build -b html examples/hello_world examples/hello_world/_build/html
open examples/hello_world/_build/html/index.html
```

If you want me to configure Pages to use the `gh-pages` branch or add a
custom domain, I can add instructions or a workflow step for that.

Repository landing page

- The repository includes an `index.html` at its root which redirects to the
	hosted documentation: https://bitvortex.github.io/OSQAr/ — GitHub Pages is
	the canonical location for the built HTML.
- If you prefer the repository's GitHub UI landing page to show the documentation
	directly, note that GitHub displays `README.md` on the repository page; an
	HTML `index.html` in the repository root will not replace that view. The
	recommended approach is to keep `README.md` minimal and provide a link to
	the Pages site (as done here).

