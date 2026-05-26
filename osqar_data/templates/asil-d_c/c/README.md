# ASIL D SEooC Qualification Project (C)

ISO 26262 SEooC qualification attempt targeting ASIL D for a C library
using the [OSQAr](https://github.com/BitVortex/OSQAr) framework.

## Structure

```
├── 01_requirements.rst       # Software safety requirements (REQ_SSR_*)
├── 02_architecture.rst       # Software architecture (ARCH_*)
├── 03_verification.rst       # Verification activities (VER_*)
├── 04_implementation.rst     # Source inventory, build config (IMPL_*)
├── 05_test_results.rst       # Test results, coverage, static analysis
├── 06_lifecycle_management.rst # AoUs, CM, tool qualification (LM_*)
├── conf.py                   # Sphinx configuration with sphinx-needs
├── index.rst                 # Master toctree + qualification summary
├── osqar_project.json        # Build/test/analysis commands
├── build-and-test.sh         # Full verification pipeline
├── include/project.h         # Library public API
├── src/project.c             # Library implementation
└── tests/test_project.c      # Unit tests
```

## Quickstart

**1. Install docs dependencies:**

```bash
python3 -m pip install -r requirements-docs.txt
# or: poetry install
```

**2. Build qualification docs:**

```bash
osqar build-docs
# or: python3 -m sphinx -b html -W . _build/html
```

**3. Run verification pipeline:**

```bash
./build-and-test.sh all
```

**4. Check traceability:**

```bash
osqar traceability _build/html/needs.json --test-prefix VER_ --code-prefix IMPL_
```

**5. Package shipment:**

```bash
osqar shipment prepare --project .
```

## Content-Authoring Guidance

This template follows ISO 26262-6:2018 for software-level product development.
For guidance on authoring the RST documents, load the `iso26262-part6-software`
skill. For compliance documentation generation, load `compliance-documentation`.

## ASIL D Key Requirements

- **No dynamic allocation after initialization** (Part 6 Table 7: ++)
- **No recursion** (Part 6 Table 7: ++)
- **One entry, one exit per function** (Part 6 Table 7: ++)
- **MC/DC coverage** at unit level (Part 6 Table 10: ++)
- **Static analysis** enforced by tool (Part 6 Table 9: ++)
- **MISRA C:2012** or equivalent coding standard
- **5 Assumptions of Use** documented for SEooC (Part 10 §9.4.2)

## License

This qualification project is provided under the Apache-2.0 license.
The OSQAr framework is Apache-2.0 licensed.
