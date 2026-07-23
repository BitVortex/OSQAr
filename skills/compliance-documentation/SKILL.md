---
name: compliance-documentation
description: Generate audit-ready qualification documentation from OSQAr needs. Automate traceability matrices, compliance checklists, gap analyses, evidence indices, and assessment-ready reports mapped to ISO 26262, ISO 21434, and ISO 21448 clauses.
version: 1.0.0
license: Apache-2.0
---

# Compliance Documentation Generation with OSQAr

## Overview

This skill covers generating audit-ready compliance documentation from OSQAr
qualification projects. It maps OSQAr's structured needs (`REQ_`, `ARCH_`, `VER_`,
`IMPL_`, `LM_`, `SC_`) to compliance artifacts required by ISO 26262, ISO 21434,
and ISO 21448 assessments.

The goal is to produce documentation that an independent assessor can use to
verify that the qualification covers all required lifecycle activities with
appropriate rigour for the target integrity level.

## When to Use

- Preparing for a functional safety assessment (ISO 26262-2 §6.4.12)
- Generating a cybersecurity assessment report (ISO/SAE 21434 §6.4.8)
- Producing a SOTIF release documentation package (ISO 21448 §12)
- Creating an auditable evidence index for a safety case
- Performing a pre-assessment gap analysis
- Documenting compliance with UN R155/R156 regulatory requirements

## Compliance Document Types

### 1. Traceability Matrix

The foundation of all compliance documentation. Maps requirements through
architecture, implementation, and verification with bidirectional links.

**Generate from OSQAr:**

```bash
# CSV (universal spreadsheet format)
osqar traceability _build/html/needs.json     --format csv     --format-output traceability_matrix.csv     --test-prefix VER_ --code-prefix IMPL_

# Excel (for assessor review)
osqar traceability _build/html/needs.json     --format xlsx     --format-output traceability_matrix.xlsx     --test-prefix VER_ --code-prefix IMPL_
```

**Expected columns:**

| Column | Content | Compliance Significance |
|--------|---------|------------------------|
| REQ_ID | Requirement identifier | Must match requirement specification |
| REQ_Title | One-line description | Must be specific and verifiable |
| Status | active/draft/obsolete | Only active needs are in scope |
| Tags | ASIL/domain tags | Shows ASIL allocation, safety relevance |
| ARCH_Linked | Architecture elements implementing this REQ | Allocation trace context: ISO 26262-6 §7.4.6 |
| VER_Linked | Verification activities testing this REQ | Required per ISO 26262-6 §9.4 |
| IMPL_Linked | Implementation elements realizing this REQ | Required per ISO 26262-6 §8.4 |
| LM_Linked | Lifecycle management elements | Required for SEooC AoUs |

**Compliance rule:** Every REQ_ at ASIL C/D must have at least one ARCH_,
one VER_, and one IMPL_ link. Missing links are traceability violations
and will be flagged by `osqar traceability`.

### 2. Standards Compliance Checklist

Map every OSQAr need to a specific ISO clause to demonstrate coverage.

```rst
.. csv-table:: ISO 26262-6 Compliance Checklist
   :header: "ISO 26262-6 Clause", "Requirement", "OSQAr Need(s)", "Status"
   :widths: 20, 40, 30, 10

   "§6.4.1", "Software safety requirements specification",
   "REQ_SSR_* (14 needs)", "✓"
   "§6.4.2", "SSR attributes (ID, ASIL, status, trace)",
   "REQ_SSR_* (all have :id:, :tags:, :links:)", "✓"
   "§7.4.3", "Software architectural design principles",
   "ARCH_* (8 needs)", "✓"
   "§7.4.14", "Verification of software architectural design",
   "REVIEW_ARCH_* (3 needs)", "✓"
   "§8.4.4", "Software unit design and implementation",
   "IMPL_UNIT_* (5 needs)", "✓"
   "§9.4", "Software unit verification",
   "VER_UNIT_* (12 needs) including coverage", "✓"
   "§9.4", "Structural coverage — MC/DC (ASIL D)",
   "VER_COVERAGE_MCDC", "✓"
   "§10.4", "Software integration and testing",
   "VER_INTEGRATION_* (6 needs)", "✓"
   "§11.4", "Testing of embedded software",
   "VER_EMBEDDED_* (4 needs)", "⚠ Partial"
```

Always include a gap column: "✓ Covered", "⚠ Partial", "✗ Not Addressed".
Partial coverage must include a mitigation description.

### 3. Gap Analysis Report

Identify and justify any standard requirements that are not fully addressed.

```rst
.. list-table:: Gap Analysis — ISO 26262-6
   :header-rows: 1

   * - Clause
     - Gap Description
     - Justification / Mitigation
   * - §11.4.3 (Embedded-software test-case derivation)
     - Applicable test-case derivation methods have not yet been selected
     - Mitigation: derive and review cases against the software requirements
       and justify the project-selected methods
   * - §9.4.5 (Software-unit test environment)
     - Unit tests currently run only in a host environment
     - Mitigation: evaluate environment representativeness and document any
       additional target or target-like verification needed for this project
   * - ISO 26262-8:2018 Clause 11 (Confidence in the use of software tools)
     - The compiler use case has not yet received a reviewed tool-confidence analysis
     - Mitigation: assess the actual use, tool impact, and error-detection measures;
       record classification and any qualification action supported by that analysis
```

OSQAr's `verification.gaps` configuration in `osqar_project.json` auto-generates
a gap table during `osqar shipment prepare`:

```json
"verification": {
  "gaps": [
    {
      "activity": "MC/DC coverage for rarely-invoked error handlers",
      "status": "accepted",
      "reason": "Error handlers triggered by fault injection, not normal execution",
      "description": "2 error paths in safety shutdown sequence cannot be
        reached during normal unit testing; verified via fault injection instead",
      "mitigation": "Fault injection test VER_FAULT_INJECT_003 exercises both paths;
        rationale documented and accepted by safety assessor"
    }
  ]
}
```

### 4. Evidence Index

A structured catalogue of all verification evidence with provenance.

```rst
.. list-table:: Verification Evidence Index
   :header-rows: 1

   * - Evidence ID
     - Type
     - Tool / Method
     - Tool Version
     - Date
     - Linked Needs
     - File / Artifact
   * - EVID-001
     - Unit test results
     - CUnit 3.2.7
     - 3.2.7
     - 2026-05-26
     - VER_UNIT_001..VER_UNIT_012
     - _build/test_results.xml
   * - EVID-002
     - Statement coverage
     - gcov/lcov
     - 1.16
     - 2026-05-26
     - VER_COVERAGE_STMT
     - coverage_report.txt
   * - EVID-003
     - Branch coverage
     - gcov/lcov
     - 1.16
     - 2026-05-26
     - VER_COVERAGE_BRANCH
     - coverage_report.txt
   * - EVID-004
     - MC/DC coverage
     - gcov/lcov
     - 1.16
     - 2026-05-26
     - VER_COVERAGE_MCDC
     - coverage_report.txt
   * - EVID-005
     - Static analysis
     - cppcheck
     - 2.14.0
     - 2026-05-26
     - VER_STATIC_001
     - cppcheck_report.xml
   * - EVID-006
     - Dynamic analysis
     - Valgrind/Memcheck
     - 3.22.0
     - 2026-05-26
     - VER_MEMCHECK
     - valgrind_report.txt
```

**OSQAr project rule:** Every evidence entry must include tool name AND version.
ISO 26262-8:2018 Clause 11 is the researched tool-confidence reference; do not
attribute this exact field rule to a subclause.

### 5. Assessment Readiness Report

A pre-assessment self-check to identify issues before the independent assessor does.

```rst
.. list-table:: Assessment Readiness Self-Check
   :header-rows: 1

   * - Check
     - Criterion
     - Status
     - Finding
   * - A1
     - All REQ_ needs have :status: active
     - ✓
     - 0 draft/obsolete needs in scope
   * - A2
     - No orphan requirements (REQ_ without ARCH_/VER_ links)
     - ✓
     - All 14 REQ_ have ≥1 ARCH_ + ≥1 VER_ link
   * - A3
     - Bidirectional traceability verified
     - ✓
     - osqar traceability returns 0 violations
   * - A4
     - Evidence from live tool runs
     - ✓
     - All VER_ evidence generated by automated tools
   * - A5
     - Tool versions documented
     - ⚠
     - EVID-007 (complexity analysis) missing lizard version
   * - A6
     - No overclaiming in documentation
     - ✓
     - All claims use "qualification attempt targeting ASIL D" language
   * - A7
     - Assumptions of Use documented
     - ✓
     - 5 AoUs in LM_ needs, traceable to REQ_EXTASSUME_*
   * - A8
     - Safety case complete
     - ✓
     - SC_TOP goal decomposed to SC_SUBGOAL_* → VER_* evidence
   * - A9
     - Confirmation measures planned
     - ⚠
     - Review independence levels documented but assessment not yet scheduled
   * - A10
     - Shipment manifest consistent
     - ✓
     - osqar checksum verify passes, SHA256SUMS complete
```

### 6. Multi-Standard Compliance Matrix

For projects covering multiple standards, generate a cross-standard matrix.

```rst
.. list-table:: Multi-Standard Compliance Overview
   :header-rows: 1

   * - Domain
     - Standard
     - OSQAr Needs
     - Evidence
     - Status
   * - Functional Safety
     - ISO 26262-6
     - REQ_SSR_*, ARCH_*, VER_*
     - EVID-001..EVID-020
     - ✓ Complete
   * - Functional Safety
     - ISO 26262-8 (Supporting)
     - LM_TOOL_*, LM_CONFIG_*
     - EVID-021..EVID-024
     - ✓ Complete
   * - Cybersecurity
     - ISO/SAE 21434 §9-§15
     - REQ_CYB_*, ARCH_CYB_*, VER_CYB_*
     - EVID-030..EVID-040
     - ✓ Complete
   * - Cybersecurity Reg.
     - UN R155
     - LM_CYB_* (organizational)
     - EVID-041..EVID-043
     - ⚠ Partial (CSMS evidence pending)
   * - SOTIF
     - ISO 21448 §5-§12
     - REQ_SOTIF_*, VER_SOTIF_*
     - EVID-050..EVID-060
     - ⚠ Partial (Area 3 validation ongoing)
```

## Automation Patterns

### Automated Compliance Report Generation

```bash
#!/bin/bash
# Generate all compliance artifacts from a single needs.json
PROJECT="."

# 1. Traceability matrix (CSV + XLSX)
osqar traceability _build/html/needs.json     --format csv --format-output _compliance/traceability.csv     --test-prefix VER_ --code-prefix IMPL_
osqar traceability _build/html/needs.json     --format xlsx --format-output _compliance/traceability.xlsx     --test-prefix VER_ --code-prefix IMPL_

# 2. Impact analysis (on top-level safety requirement)
osqar impact _build/html/needs.json     --need-id REQ_SSR_SAFETY_001     --direction downstream --max-depth 10     --json-report _compliance/impact_analysis.json

# 3. Baseline comparison (if previous baseline exists)
osqar baseline diff v1.0 current     --json-report _compliance/baseline_diff.json

# 4. Gap analysis (from osqar_project.json)
osqar shipment prepare --project . --skip-verification

# 5. Shipment packaging with GPG signature
osqar shipment prepare --project .
osqar checksum generate --root _shipment --output _shipment/SHA256SUMS
osqar sign create --manifest _shipment/SHA256SUMS --key qualification@example.com

echo "Compliance artifacts generated in _compliance/ and _shipment/"
```

### Continuous Integration for Compliance

```yaml
# .github/workflows/compliance.yml
name: Compliance Documentation

on:
  push:
    tags: ['*-*']  # libversion-osqarversion format

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install OSQAr
        run: pip install git+https://github.com/BitVortex/OSQAr.git@main
      
      - name: Build qualification docs
        run: python3 -m sphinx -b html -W . _build/html
      
      - name: Traceability check
        run: |
          osqar traceability _build/html/needs.json             --test-prefix VER_ --code-prefix IMPL_             --json-report traceability_report.json
      
      - name: Generate compliance matrix
        run: |
          osqar traceability _build/html/needs.json             --format xlsx --format-output compliance/traceability.xlsx             --test-prefix VER_ --code-prefix IMPL_
      
      - name: Baseline snapshot
        run: |
          osqar baseline snapshot             --tag "${{ github.ref_name }}"             --message "CI snapshot at ${{ github.ref_name }}"
      
      - name: Shipment verification
        run: |
          osqar shipment prepare --project .
          osqar checksum verify --root _shipment
      
      - name: Upload compliance artifacts
        uses: actions/upload-artifact@v4
        with:
          name: compliance-docs-${{ github.ref_name }}
          path: |
            _compliance/
            _shipment/
            _build/html/needs.json
```

## Assessment Preparation Checklist

Before an independent functional safety assessment (ISO 26262-2 §6.4.12),
verify all items:

```rst
.. list-table:: Pre-Assessment Checklist
   :header-rows: 1

   * - #
     - Item
     - Evidence Location
     - Standard Reference
   * - 1
     - Safety plan approved
     - LM_SAFETY_PLAN
     - ISO 26262-2 §6.4.6
   * - 2
     - HARA completed and verified
     - REQ_SAFETY_GOAL_* (trace to HARA)
     - ISO 26262-3 §6
   * - 3
     - Functional safety concept documented
     - REQ_SSR_* + ARCH_* (FSRs + TSRs)
     - ISO 26262-3 §7; ISO 26262-4:2018 §6
   * - 4
     - Software safety requirements specified
     - REQ_SSR_* (all 14 SSRs)
     - ISO 26262-6 §6.4
   * - 5
     - Software architecture designed and reviewed
     - ARCH_* (8 architecture needs)
     - ISO 26262-6 §7.4
   * - 6
     - Software units implemented per coding standard
     - IMPL_UNIT_*, IMPL_ALLOC
     - ISO 26262-6 §8.4
   * - 7
     - Unit verification with coverage
     - VER_UNIT_*, VER_COVERAGE_*
     - ISO 26262-6 §9.4
   * - 8
     - Integration testing completed
     - VER_INTEGRATION_*
     - ISO 26262-6 §10.4
   * - 9
     - Embedded testing on target hardware
     - VER_EMBEDDED_*
     - ISO 26262-6 §11.4
   * - 10
     - Dependent failure analysis performed where applicable
     - VER_DFA
     - ISO 26262-9 §7
   * - 11
     - Safety analyses performed where applicable
     - VER_FMEA, VER_FTA
     - ISO 26262-9 §8
   * - 12
     - Tool-confidence analysis and any resulting qualification evidence assembled
     - LM_TOOL_TCL_*
     - ISO 26262-8 §11
   * - 13
     - SEooC AoUs documented (if applicable)
     - LM_AOU_*
     - ISO 26262-10 §9.1 (general guidance)
   * - 14
     - Safety case complete with evidence links
     - SC_* (all SC_ needs)
     - ISO 26262-2 §6.4.8; ISO 26262-10:2018 §5
   * - 15
     - Confirmation reviews/audit/assessment scheduled
     - LM_CONFIRMATION_*
     - ISO 26262-2 §6.4.9-§6.4.12
   * - 16
     - Release authorization documented
     - LM_RELEASE
     - ISO 26262-2 §6.4.13
```

## Multi-Standard Assessment Coordination

When assessments span multiple standards, coordinate evidence:

| Assessment Type | Standard | Timing | OSQAr Evidence |
|-----------------|----------|--------|----------------|
| Functional safety assessment | ISO 26262-2 §6.4.12 | Before SOP | REQ_/ARCH_/VER_/SC_ needs |
| Cybersecurity assessment | ISO/SAE 21434 §6.4.8 | Before SOP | REQ_CYB_/ARCH_CYB_/VER_CYB_ needs |
| SOTIF release evaluation | ISO 21448 §12 | Before SOP (ADAS) | REQ_SOTIF_/VER_SOTIF_ needs |
| CSMS audit (UN R155) | UN R155 §7 | Before type approval | LM_CYB_* (organizational) |
| SUMS audit (UN R156) | UN R156 §7 | Before type approval | LM_CYB_UPDATE |

## Pitfalls

1. **Presenting traceability as compliance** — a complete traceability matrix
   shows links exist but does not prove requirements are correct, verification
   is adequate, or evidence is valid. Traceability is necessary but not sufficient.
2. **Hand-written evidence** — assessors can identify hand-entered numbers.
   All evidence must come from automated tool output with tool name, version,
   and date under OSQAr project policy. ISO 26262-8:2018 Clause 11 is the researched
   tool-confidence context; the exact field rule remains OSQAr policy.
3. **Version drift** — compliance documentation generated at one point in time
   must match the shipped artifacts. Use OSQAr baselines to lock versions.
4. **Overclaiming compliance language** — never state "ISO 26262 compliant"
   or "ASIL D certified." Use "qualification attempt targeting ASIL D"
   and "developed per ISO 26262:2018 processes." Certification requires
   independent assessment.
5. **Missing tool-use evaluation** — evidence may be rejected when reliance on
   a tool is unsupported. Evaluate relevant tool use under ISO 26262-8:2018 Clause 11;
   classification and any qualification action follow from the reviewed use-case
   analysis, not from a fixed category assigned to the tool name.
6. **Incomplete gap justifications** — simply stating "not applicable" is
   insufficient. Every gap must explain WHY it's not applicable with
   reference to the project scope, SEooC assumptions, or standard clause
   that exempts it.
7. **Forgetting the safety manual** — for SEooC qualification, the safety
   manual is as important as the safety case. It must be part of the
   compliance documentation package.
