# OSQAr Skills Index

This directory contains reusable skills for authoring OSQAr qualification content
for automotive functional safety, cybersecurity, and SOTIF projects.

All skills are self-contained, public-safe, and reference ISO standards by
clause number only — no verbatim standard text, no proprietary information.

## In-Repository Content-Authoring Skills

These skills are **shipped with OSQAr** and cover *what* to write in qualification
RST documents. They map specific ISO clauses to OSQAr need types with ASIL-differentiated
guidance and concrete RST examples.

| # | Skill | Purpose | Primary Standards |
|---|-------|---------|-------------------|
| 1 | `iso26262-part6-software` | Author ISO 26262-6 software requirements, architecture, and verification for OSQAr | ISO 26262 Parts 2,4,6,8,9,10 |
| 2 | `security-coengineering` | Add ISO 21434 cybersecurity qualification to OSQAr projects — TARA, CAL, UN R155/R156 | ISO/SAE 21434, UN R155/R156 |
| 3 | `sotif-qualification` | Add ISO 21448 SOTIF qualification for ADAS/autonomous systems — triggering events, zone model, scenario-based validation | ISO 21448:2022 |
| 4 | `vehicle-program-qualification` | Scale OSQAr from single-component SEooC to multi-ECU, multi-supplier vehicle programs | ISO 26262 Parts 2,4,7,8,10 |
| 5 | `compliance-documentation` | Generate audit-ready compliance documentation from OSQAr needs — traceability matrices, gap analyses, evidence indices, assessment checklists | ISO 26262, ISO 21434, ISO 21448 |

## Research Profile Skills (External, Agent-Only)

These skills are part of the Hermes Agent research profile and are NOT shipped
with OSQAr. They provide **deep domain knowledge** — clause-level requirements,
hazard analysis methods, and cross-standard navigation — that informs the
*what* to write when using the content-authoring skills above.

When an agent is assisting with OSQAr qualification, it SHOULD load the
relevant research skills alongside the content-authoring skills. The two
skill sets are complementary: research skills provide the domain knowledge;
content-authoring skills provide the OSQAr-specific mapping.

### Core Research Skills

| # | Skill | Purpose | Relationship to OSQAr |
|---|-------|---------|----------------------|
| R1 | `functional-safety-index` | Master navigation hub for all functional safety knowledge — load FIRST when entering any FS task | Routes to the right skills; minimizes context window usage |
| R2 | `functional-safety-fundamentals` | IEC 61508 domain-independent FS: SIL, safety lifecycle, safety cases, cross-domain equivalence | Foundational knowledge — always useful background |
| R3 | `iso-26262-application` | ISO 26262:2018 full coverage: 65 clause-level requirements (R-001 through R-065), V-model traceability, ASIL determination, SEooC, confirmation measures | Primary reference for automotive software AND hardware safety content |
| R4 | `hazard-analysis-methods` | FMEA, FTA, STPA, HAZOP, HARA — detailed method procedures, worksheet templates, S/E/C tables | Essential for authoring VER_FMEA/VER_FTA/VER_DFA needs |
| R5 | `iso-21434-application` | ISO/SAE 21434 cybersecurity: TARA, CAL determination, CSMS, incident response | Complements `security-coengineering` with deeper clause knowledge |
| R6 | `iso-21448-application` | ISO 21448 SOTIF: zone model, triggering events, validation strategies, ML/AI gaps | Complements `sotif-qualification` with deeper clause knowledge |
| R7 | `cyber-physical-systems-engineering` | Real-time analysis, communication protocols, safety architectures, formal verification | Needed for embedded/hardware timing analysis in qualification |

### Structure Skills (Clause Hierarchy Reference)

These skills contain clause hierarchy (numbers + titles only — NO verbatim text)
and are usable by any agent with no Hindsight dependency:

| # | Skill | Content |
|---|-------|---------|
| S1 | `iso-26262-structure` | ISO 26262:2018 clause hierarchy — all 12 parts, 663 clauses |
| S2 | `iso-21434-structure` | ISO/SAE 21434:2021 clause hierarchy — Clauses 5-15 |
| S3 | `iso-21448-structure` | ISO 21448:2022 clause hierarchy |
| S4 | `iec-61508-structure` | IEC 61508:2010 clause hierarchy — Parts 1-5, 7 |
| S5 | `iso-pas-8926-structure` | ISO PAS 8926 (AI functional safety, draft) clause hierarchy |

## Recommended Reading Order

### For new OSQAr users
1. Start with the [OSQAr documentation](https://osqar.nousresearch.com) for tool basics
2. Load `iso26262-part6-software` for software qualification content guidance
3. Load `compliance-documentation` to understand what audit-ready output looks like
4. Load `vehicle-program-qualification` when scaling beyond a single component

### For agents assisting with qualification
1. Load ``functional-safety-index`` → follow the task routing to identify needed research skills
2. Load the content-authoring skill matching the work scope (software, cybersecurity, SOTIF)
3. Load ``iso-26262-application`` for clause-level requirements backing
4. Load ``hazard-analysis-methods`` if authoring safety analysis verification needs
5. Load ``compliance-documentation`` when preparing assessment artifacts

### For automotive software SEooC qualification (most common case)
1. ``functional-safety-index`` → routes to research skills
2. ``iso-26262-application`` → Part 6 clause requirements + Part 10 SEooC guidance
3. ``iso26262-part6-software`` → author REQ_SSR_/ARCH_/VER_ needs
4. ``hazard-analysis-methods`` → if FMEA/FTA needs are required
5. ``compliance-documentation`` → traceability matrix, gap analysis, pre-assessment checklist
6. ``vehicle-program-qualification`` → if multi-ECU or supplier integration applies

### For cybersecurity/safety co-engineering
1. `iso26262-part6-software` for safety baseline
2. `security-coengineering` for cybersecurity extensions
3. `iso-21434-application` for TARA clause-level requirements
4. `compliance-documentation` for cross-standard evidence packaging
5. `vehicle-program-qualification` for multi-supplier integration

### For ADAS/autonomous systems
1. `iso26262-part6-software` for safety baseline
2. `sotif-qualification` for SOTIF-specific qualification
3. `iso-21448-application` for SOTIF clause-level requirements
4. `compliance-documentation` for assessment-ready SOTIF documentation
5. `vehicle-program-qualification` for sensor fusion + cross-ECU qualification

### For assessment preparation
1. `compliance-documentation` for the full assessment readiness workflow
2. `iso-26262-application` to verify clause-level coverage against all 65 requirements
3. Load any domain-specific skill relevant to the assessment scope
4. Use clause structure skills to verify clause references before presenting to assessor

## Skill Interaction Pattern

```
Research Skills (domain knowledge)     Content-Authoring Skills (OSQAr mapping)
─────────────────────────────         ─────────────────────────────────────
iso-26262-application                  iso26262-part6-software
  "ISO 26262-6 §9.4 requires MC/DC       "Use VER_COVERAGE_MCDC need with
   for ASIL D unit testing"              :tags: ASIL_D;coverage;MC/DC"

functional-safety-fundamentals         compliance-documentation
  "Safety case requires GSN structure    "osqar traceability --format xlsx
   with goals, strategies, solutions"    exports SC_* needs to spreadsheet"

hazard-analysis-methods                (applicable to all content-authoring skills)
  "FMEA classifies failures by           "Use VER_FMEA need with failure
   safety impact at each level"          mode classification in :links:"
```

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
- Substitute for a competent functional safety engineer
