# Using the OSQAr Architecture Boilerplate (Example-Driven Guide)

This guide explains how to use OSQAr (Open Safety Qualification Architecture) as a **documentation-first** boilerplate to produce safety/compliance artifacts with:

- structured requirements (via **sphinx-needs**)
- architecture diagrams (via **PlantUML**)
- verification planning and traceability (requirements ↔ architecture ↔ tests)
- optional embedding/import of test results (e.g., **JUnit XML**)

The guidance below is based on the shared TSIM example documentation and its language-specific implementations:

- `examples/c_hello_world/`
- `examples/cpp_hello_world/`
- `examples/rust_hello_world/`

(The original Python variant in `examples/hello_world/` remains available as a legacy/reference example.)

## 1) Quick start: build a reference example

From the repository root:

```bash
poetry install
poetry run sphinx-build -b html examples/c_hello_world _build/html/example
open _build/html/example/index.html
```

If you prefer to run the full “test → docs → traceability” workflow from within an example:

```bash
cd examples/c_hello_world
./build-and-test.sh
open _build/html/index.html
```

## 2) What OSQAr is (and what it isn’t)

OSQAr is not an application framework. It is a **documentation generator setup** that helps you create auditable artifacts:

- requirements specs
- architecture specs and diagrams
- verification plans
- traceability matrices
- (optionally) test result summaries embedded into docs

The “architecture” in OSQAr refers to the **architecture of the system you are documenting**, not the architecture of OSQAr itself.

## 3) Core workflow (the pattern to reuse)

The reference example uses a consistent chapter structure:

- `index.rst`: navigation hub (table of contents)
- `01_requirements.rst`: safety goals, safety requirements, functional requirements
- `02_architecture.rst`: architecture specs + PlantUML diagrams
- `03_verification.rst`: verification strategy + TEST_* needs + traceability matrix
- `04_implementation.rst`: implementation notes + mapping hints
- `05_test_results.rst`: how to generate test results and how to connect them back

### A) Define needs objects (requirements, architecture, tests)

OSQAr relies on **sphinx-needs**. The building block is the `.. need::` directive with an `:id:`.

Example pattern (from `examples/hello_world/01_requirements.rst`):

```rst
.. need:: (SR) The system shall detect when temperature exceeds the safe operating limit and report an unsafe state within 100ms.
   :id: REQ_SAFETY_002
   :status: active
   :tags: thermal, detection, timing
   :links: REQ_SAFETY_001, ARCH_FUNC_003, ARCH_SIGNAL_003

   **Architecture**: :need:`ARCH_FUNC_003`
   **Tests**: :need:`TEST_END_TO_END_001`
```

Key ideas:

- `:id:` is the stable, audit-friendly identifier.
- `:links:` creates trace links (and sphinx-needs will create backlinks).
- `:need:` creates clickable references in the rendered HTML.

### B) Use structured IDs (enforced)

The boilerplate enforces a simple rule in `conf.py`:

- IDs must match `^[A-Z0-9_]{3,}`

In practice, use a prefix system so humans can visually classify artifacts:

- `REQ_SAFETY_*` — safety goals/requirements
- `REQ_FUNC_*` — functional requirements
- `ARCH_*` — architecture and design constraints
- `TEST_*` — verification requirements / test specifications
- `CODE_*` — optional “implementation anchors” if you want to reference code sections

This naming is domain-agnostic: you can reuse the same structure for medical, machinery, robotics, automotive, etc.

### C) Add architecture diagrams (PlantUML) and link them to needs

The example places PlantUML sources in `examples/hello_world/diagrams/` and includes them from `02_architecture.rst`.

Typical include pattern:

```rst
.. uml:: diagrams/02_data_flow.puml
   :caption: Data flow (budget: :need:`REQ_SAFETY_002`) — Architecture: :need:`ARCH_FUNC_001`, :need:`ARCH_FUNC_002`, :need:`ARCH_FUNC_003`
```

This keeps your diagrams:

- version-controlled
- reviewable in diff
- traceable to requirements (through captions and `:links:` fields)

### D) Create a verification chapter that defines TEST_* needs

A useful verification chapter contains two things:

1) **Test requirements** as needs objects (IDs like `TEST_*`)
2) A **traceability matrix** (often as a list-table) that maps REQ/ARCH → TEST

In the example, the verification chapter is the source of truth for what is tested.

### E) Run tests and keep machine-readable results

Each example uses language-appropriate tooling to generate JUnit XML.

For example, the legacy Python variant uses pytest with JUnit output:

```bash
poetry run pytest tests/test_tsim.py -v --junit-xml=test_results.xml
```

Treat the resulting `test_results.xml` as a compliance artifact you can:

- archive
- attach to releases
- publish with the generated HTML docs

## 4) Recommended repository layout for your own project

If you’re starting a new system, the simplest approach is:

1) Copy the example folder as a template
2) Replace the content (requirements/diagrams/tests) with your system’s artifacts

Suggested layout (mirrors the example):

```
my_system_docs/
  conf.py
  index.rst
  01_requirements.rst
  02_architecture.rst
  03_verification.rst
  04_implementation.rst
  05_test_results.rst
  diagrams/
  src/
  tests/
```

Notes:

- Keeping `src/` and `tests/` alongside docs is optional, but it makes “docs ↔ code ↔ tests” traceability much easier.
- Keep `_build/` out of version control.

## 5) Configuration: what matters in conf.py

At minimum, you need:

- `sphinx_needs` enabled (core traceability)
- `sphinxcontrib.plantuml` enabled (architecture diagrams)
- `needs_id_regex` set (ID discipline)

The example configuration (see `examples/hello_world/conf.py`) also:

- defaults to the `furo` theme but allows `OSQAR_SPHINX_THEME` override
- renders PlantUML to `svg`
- supports multiple PlantUML execution strategies:
  - local jar via `PLANTUML_JAR`
  - system `plantuml`
  - fallback to the public PlantUML server

## 6) Linking and “click-through traceability” (how to make it feel good)

To create a smooth review experience:

- Always include **forward links** (REQ → ARCH, REQ → TEST)
- Use `:links:` for machine-usable relationships
- Use `:need:` references in:
  - narrative text (e.g., “implements :need:`REQ_FUNC_001`”)
  - diagram captions
  - tables (traceability matrices)

For deeper patterns and examples, see:

- `examples/hello_world/LINKED_TRACEABILITY_GUIDE.md`

## 7) Test results in the docs: two practical options

### Option A (lightweight): document how to generate results and link them

This is the lowest friction path:

- generate `test_results.xml`
- describe how it’s produced and where to find it
- use tables in `05_test_results.rst` that reference `TEST_*` needs

This still produces strong compliance artifacts because your traceability is explicit and your test output is archived.

### Option B (embedded): import/visualize JUnit results in Sphinx

If you want the docs build to parse and render the JUnit XML, enable the appropriate Sphinx extension and configuration.

The repository already depends on `sphinx-test-reports` (see `pyproject.toml`). A typical setup looks like:

```python
# conf.py
extensions = [
    'sphinx_needs',
    'sphinxcontrib.plantuml',
  'sphinxcontrib.test_reports',
]

test_reports = ['test_results.xml']
```

Then your RST can include the reports where you want them.

If you want stricter mapping (TEST_* ↔ REQ_*), consider maintaining an explicit mapping (documented in the example’s implementation chapter) and generating a matrix/table from it.

## 8) CI/CD and artifact packaging

The example is already wired to publish HTML to GitHub Pages from `examples/hello_world`.

A typical CI workflow for a documentation+compliance build is:

1) run tests and produce JUnit XML
2) build docs (including diagrams)
3) upload artifacts:
   - `_build/html/`
   - `test_results.xml`

## 9) Common pitfalls (and how to avoid them)

- **IDs don’t match the regex**: keep IDs uppercase and underscore-separated.
- **Broken links**: prefer `:need:` references over plain text IDs.
- **PlantUML in offline environments**: set `PLANTUML_JAR` or install `plantuml` locally to avoid the web-service fallback.
- **Extension order**: keep `sphinx_needs` early; it’s the core dependency for traceability features.

---

If you’d like, I can also add a Sphinx page (RST) version of this guide and wire it into the example’s `index.rst` so it’s browsable inside the generated HTML, not just on GitHub.
