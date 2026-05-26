# OSQAr Skills Index

This directory contains reusable skills for authoring OSQAr qualification content
for automotive functional safety, cybersecurity, and SOTIF projects.

All skills are self-contained, public-safe, and reference ISO standards by
clause number only — no verbatim standard text, no proprietary information.

## Skills

| # | Skill | Purpose | Primary Standards |
|---|-------|---------|-------------------|
| 1 | `iso26262-part6-software` | Author ISO 26262-6 software requirements, architecture, and verification for OSQAr | ISO 26262 Parts 2,4,6,8,9,10 |
| 2 | `security-coengineering` | Add ISO 21434 cybersecurity qualification to OSQAr projects | ISO/SAE 21434, UN R155/R156 |
| 3 | `sotif-qualification` | Add ISO 21448 SOTIF qualification for ADAS/autonomous systems | ISO 21448:2022, ISO/PAS 21448:2019 |
| 4 | `vehicle-program-qualification` | Scale OSQAr from single-component SEooC to multi-ECU, multi-supplier vehicle programs | ISO 26262 Parts 2,4,7,8,10 |
| 5 | `compliance-documentation` | Generate audit-ready compliance documentation from OSQAr needs — traceability matrices, gap analyses, evidence indices, assessment checklists | ISO 26262, ISO 21434, ISO 21448 |

## Recommended Reading Order

### For new OSQAr users
1. Start with the [OSQAr documentation](https://osqar.nousresearch.com) for tool basics
2. Load `iso26262-part6-software` for software qualification content guidance
3. Load `compliance-documentation` to understand what audit-ready output looks like
4. Load `vehicle-program-qualification` when scaling beyond a single component

### For cybersecurity/safety co-engineering
1. Load `iso26262-part6-software` for safety baseline
2. Load `security-coengineering` for cybersecurity extensions
3. Load `compliance-documentation` for cross-standard evidence packaging
4. Load `vehicle-program-qualification` for multi-supplier integration

### For ADAS/autonomous systems
1. Load `iso26262-part6-software` for safety baseline
2. Load `sotif-qualification` for SOTIF-specific qualification
3. Load `compliance-documentation` for assessment-ready SOTIF documentation
4. Load `vehicle-program-qualification` for sensor fusion + cross-ECU qualification

### For assessment preparation
1. Load `compliance-documentation` for the full assessment readiness workflow
2. Load `iso26262-part6-software` to verify requirements coverage
3. Load any domain-specific skill relevant to the assessment scope

## Design Principles

- **No verbatim standard text** — clauses are referenced by number, not quoted
- **No proprietary information** — purely public-domain knowledge from published standards
- **No company references** — no tool names beyond OSQAr itself and common open-source tools
- **Self-contained** — each skill can be used independently; cross-references use skill names
- **Public-safe** — suitable for inclusion in a public open-source repository
- **ASIL-differentiated** — guidance varies by ASIL where the standard varies
- **Clause-cited** — all standard claims include clause references for verification

## Non-Goals

These skills do NOT:
- Replace reading the actual ISO standards (normative requirements come from the standards)
- Provide legal or compliance advice (qualification requires independent assessment)
- Cover non-automotive domains (railway, medical, aviation have their own standards)
- Include company-internal processes or proprietary workflows
