# OSQAr AI Coding Agent Instructions

## Project Overview

**OSQAr** (Open Safety Qualification Architecture) is an open functional safety standard specification for Safety Elements out of Context (SEooC), compliant with ISO 26262 requirements. It's implemented as a Sphinx-based documentation boilerplate designed to be **domain-agnostic**—applicable to medical devices, robots, machinery, automotive, and other safety-critical systems. It's not a runtime application—it's a static documentation generator that combines requirements management, test traceability, and architecture visualization to formalize safety qualifications.

### Core Technology Stack

- **Sphinx** (^7.2): Static documentation generator
- **sphinx-needs** (^2.0): The critical engine for requirements traceability, linking requirements to implementation
- **sphinx-test-reports** (^1.0): Imports JUnit/TRF test results into documentation
- **sphinxcontrib-plantuml** (^0.25): Architecture diagrams via PlantUML
- **sphinx-press-theme** (^0.8): Clean HTML theme
- **Poetry**: Python dependency management

## Architecture & Patterns

### The "Why" Behind Design

OSQAr enforces structured requirement IDs (`needs_id_regex = '^[A-Z0-9_]{3,}'`) to create **traceability matrices** required by ISO 26262 (and similar standards like IEC 61508, ISO 13849). This links:
- **Safety Requirements** (REQ_SAFETY_*) from ISO 26262 tables
- **Implementation & Design** specifications
- **Verification & Test Results** (via sphinx-test-reports)

This is a **documentation-first** architecture where `conf.py` is the project nucleus defining how Sphinx processes needs objects. The design enforces compliance artifact generation for functional safety qualification and certification processes.

### Key Components

1. **`conf.py`**: Sphinx configuration hub
   - Defines extension loading order: `sphinx_needs` must come before other traceability extensions
   - Sets `needs_id_regex` to enforce standardized requirement IDs (e.g., `REQ_001`, `ARCH_DB_001`)
   - Configures PlantUML rendering (can use local JAR or web service)

2. **`pyproject.toml`**: Poetry project manifest
   - `package-mode = false` because this is a documentation project, not a Python package
   - Core dependencies locked to maintain reproducible documentation builds
   - Dev tools: pytest (for documentation tests), black (code formatting)

3. **Documentation content**: Lives in `.rst` files (not yet visible—would be created in `source/` or similar)

## Developer Workflows

### Build Documentation

```bash
poetry install  # Install dependencies
sphinx-build -b html . _build/html  # Build HTML output
```

### Run Tests

```bash
pytest  # Run any tests (documentation tests or conf.py validation)
black --check .  # Lint code style
```

### Expected Directory Structure (When Content Added)

```
OSQAr/
├── conf.py                 # Sphinx config (requirements ID enforcement)
├── pyproject.toml          # Poetry manifest
├── index.rst               # Documentation entry point
├── requirements/           # .rst files with needs objects
├── architecture/           # PlantUML diagrams
└── _build/                 # Generated output (do not commit)
```

## Project-Specific Conventions

1. **Requirement ID Format**: Must match `^[A-Z0-9_]{3,}` 
   - Examples: `REQ_SAFETY_001`, `REQ_FUNCTIONAL_002`, `ARCH_PATTERN_02`, `TEST_VERIFICATION_001`
   - Prefix categories correspond to ISO 26262 artifact types (safety requirements, functional requirements, architectural requirements, verification methods)

2. **Sphinx-needs Objects**: Use `.. need::` directive with traced IDs
   - Each need must declare its status, type, and traceability links to upstream/downstream artifacts
   - Automated traceability ensures no unverified requirements (ISO 26262 compliance)

3. **PlantUML Integration**: Architecture diagrams should use SVG output for web rendering
   - Diagrams must show ASIL decomposition, data flows, and SEooC boundaries where applicable
   - Reference domain-specific patterns but maintain domain-agnostic notation

4. **Package Mode**: Always keep `package-mode = false` in pyproject.toml—this is not a pip-installable package

5. **Domain-Agnostic Applicability**: When adding examples or patterns, ensure they work across automotive, medical, robotics, and machinery domains without domain-specific assumptions

## Integration Points & Dependencies

- **sphinx-needs** integrates with reStructuredText directives (`.rst` files) to parse and link requirements
## Common Patterns to Apply

1. **When adding requirements**: Use structured IDs and `needs_id_regex`-compliant naming
   - Link to ISO 26262 source material or applicable standard (IEC 61508, ISO 13849, etc.)
   - Include traceability back to safety goals and forward to verification methods

2. **When linking test results**: Use sphinx-test-reports configuration in `conf.py`
   - Ensure test reports map to verification requirements for compliance artifact generation

3. **When modifying conf.py**: Always test with `sphinx-build` to catch extension ordering issues
   - Validate that needs IDs follow `^[A-Z0-9_]{3,}` regex after changes

4. **When adding diagrams**: Use PlantUML syntax in `.diagram` or `.uml` files referenced from `.rst`
   - Consider ASIL levels, failure modes, and architectural patterns applicable across domains

5. **When documenting patterns**: Provide domain-agnostic examples (or multiple domain examples) to maintain cross-domain applicability
- `poetry install`: Install all dependencies
- `sphinx-build -b html . _build/html`: Build HTML documentation
- `pytest`: Run tests
- `black .`: Format code

## Common Patterns to Apply

1. **When adding requirements**: Use structured IDs and `needs_id_regex`-compliant naming
2. **When linking test results**: Use sphinx-test-reports configuration in `conf.py`
3. **When modifying conf.py**: Always test with `sphinx-build` to catch extension ordering issues
4. **When adding diagrams**: Use PlantUML syntax in `.diagram` or `.uml` files referenced from `.rst`
