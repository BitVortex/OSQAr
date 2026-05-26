---
name: security-coengineering
description: Add ISO/SAE 21434 cybersecurity qualification content to OSQAr projects. Map TARA results to OSQAr REQ/ARCH/VER needs, integrate with ISO 26262 safety case, and address UN R155/R156 regulatory requirements.
version: 1.0.0
license: Apache-2.0
---

# Cybersecurity-Safety Co-Engineering with OSQAr

## Overview

This skill maps ISO/SAE 21434:2021 (Road Vehicles — Cybersecurity Engineering) onto
OSQAr qualification artifacts for projects that require both functional safety
(ISO 26262) and cybersecurity (ISO 21434) qualification.

For security-safety co-engineering, OSQAr projects should include cybersecurity
needs alongside safety needs, with explicit link types between the two domains.

## When to Use

- Adding cybersecurity qualification to an existing OSQAr safety project
- Starting a co-engineering qualification from scratch
- Addressing UN R155 (cybersecurity) or UN R156 (software updates) regulatory requirements
- Performing TARA and needing to capture results as OSQAr needs

## Standards Context

ISO/SAE 21434:2021 specifies cybersecurity engineering for road vehicles across
the entire lifecycle. It complements ISO 26262 — safety addresses malfunctions,
cybersecurity addresses intentional attacks. Both must be addressed for
modern connected vehicles.

**Clause structure:**
- §5: Organizational cybersecurity management (governance, culture, CSMS)
- §6: Project-dependent cybersecurity management (plan, case, assessment)
- §7: Distributed cybersecurity activities (suppliers, DIA-equivalent)
- §8: Continual cybersecurity activities (monitoring, vulnerability management)
- §9: Concept phase (item definition, cybersecurity goals, concept)
- §10: Product development (design, integration, verification)
- §11: Cybersecurity validation
- §12: Production
- §13: Operations and maintenance (incident response, updates)
- §14: End of cybersecurity support and decommissioning
- §15: TARA methods (9-step: asset ID, threat scenarios, impact, attack path,
  feasibility, risk value, treatment decision)

**Regulatory context:** UN R155 (cybersecurity management system) and
UN R156 (software update management system) require documented cybersecurity
processes — OSQAr qualification artifacts serve as evidence.

## Document Structure

Add cybersecurity content to existing OSQAr files or create dedicated sections:

### 01_requirements.rst — Cybersecurity Requirements

Derive `REQ_CYB_*` needs from TARA results:

| TARA Step | OSQAr Requirement Category | ID Pattern |
|-----------|---------------------------|------------|
| Asset identification (§15.3) | Protected assets, security properties | `REQ_CYB_ASSET_*` |
| Threat scenario ID (§15.4) | Threat mitigations per STRIDE category | `REQ_CYB_THREAT_*` |
| Impact rating (§15.5) | Safety-impacted cybersecurity requirements | `REQ_CYB_IMPACT_*` |
| Attack path analysis (§15.6) | Required defence-in-depth measures | `REQ_CYB_ATTACKPATH_*` |
| Risk treatment (§15.9) | Accepted risks, transferred risks, avoided risks | `REQ_CYB_RISKTREAT_*` |

```rst
.. need:: The component shall validate all externally-sourced
          calibration data using a digital signature before application.
   :id: REQ_CYB_THREAT_001
   :status: active
   :tags: cybersecurity;tampering;calibration;TARA_step_4
   :links: ARCH_CYB_SIGNATURE;VER_CYB_FUZZ_001
   :collapsed: SAFETY_REQ_001  (safety-security link)

   **TARA source:** Threat scenario TS-003 (tampered calibration data
   causing unintended acceleration)
   **Impact:** Safety (feeds ASIL D safety goal) + Financial
   **Risk treatment:** Reduce — add digital signature verification
   **CAL target:** CAL 4 (per Annex E attack feasibility rating)
```

### 02_architecture.rst — Cybersecurity Architecture

Add `ARCH_CYB_*` needs showing security mechanisms:

```rst
.. arch:: Signature verification module: all calibration data validated
         against OEM public key before storage in NVM.
   :id: ARCH_CYB_SIGNATURE
   :tags: cybersecurity;digital_signature;secure_boot_chain
   :links: REQ_CYB_THREAT_001;VER_CYB_FUZZ_001;

   **Algorithm:** ECDSA P-256 with SHA-256
   **Key storage:** Hardware Security Module (HSM) — assumed external
   **Failure mode:** Verification failure → reject data, log event,
                     maintain previous safe calibration
```

### 03_verification.rst — Cybersecurity Verification

Add `VER_CYB_*` needs covering:

| Verification Activity | OSQAr Section | Method |
|----------------------|---------------|--------|
| Fuzz testing of external interfaces | Fuzz Testing | AFL++ / libFuzzer |
| Static analysis for security flaws | Static Analysis | cppcheck + CERT C rules |
| Vulnerability scanning of dependencies | Dependency Scan | OWASP dependency-check |
| Penetration testing scope | Penetration Testing | Defined in TARA attack paths |
| Secure code review | Security Review | Manual inspection of crypto, auth, input validation |

```rst
.. ver:: Fuzz campaign: all external parsing interfaces exercised
        for 24 CPU-hours minimum with ASan+UBSan instrumentation.
   :id: VER_CYB_FUZZ_001
   :tags: cybersecurity;fuzzing;TARA_verification
   :links: REQ_CYB_THREAT_001;ARCH_CYB_SIGNATURE

   **Tool:** AFL++ 4.09c
   **Duration:** 24h (CPU time)
   **Corpus:** 1,000 seed files covering valid + boundary + malformed
   **Instrumentation:** ASan, UBSan
   **Results:** 0 crashes, 12 unique hangs (all benign —
                intentionally slow paths with 30s timeout)
```

## Safety-Security Linkage (`:collapsed:`)

OSQAr's `:collapsed:` field provides cross-domain links between safety and
security needs (added in v0.7.3+). Use it to document co-engineering:

- Every TARA threat scenario with safety impact → linked to the relevant
  safety goal or safety requirement
- Every safety mechanism with cybersecurity relevance → linked to the
  relevant cybersecurity requirement
- Every shared verification activity → linked to both domains

```rst
.. need:: Safety goal: no unintended acceleration above 3 km/h.
   :id: REQ_SAFETY_001
   :tags: ASIL_D;safety_goal;unintended_acceleration

.. need:: Cybersecurity requirement: validate calibration signatures.
   :id: REQ_CYB_THREAT_001
   :collapsed: REQ_SAFETY_001
```

## Cybersecurity Case Integration

Per ISO/SAE 21434 §6.4.7, the cybersecurity case is analogous to the
ISO 26262 safety case. In OSQAr:

```rst
.. sc:: Cybersecurity claim: the component is resilient to
       remote attacks on its external interfaces at CAL 4.
   :id: SC_CYB_TOP
   :links: SC_CYB_SUBGOAL_1;SC_CYB_SUBGOAL_2
   :collapsed: SC_SAFETY_TOP

.. sc:: Sub-claim: all externally-sourced data is
       cryptographically verified before use.
   :id: SC_CYB_SUBGOAL_1
   :links: REQ_CYB_THREAT_001;ARCH_CYB_SIGNATURE;VER_CYB_FUZZ_001
```

## Lifecycle Management — Cybersecurity Additions

Add cybersecurity-specific lifecycle management to `06_lifecycle_management.rst`:

| LM Need | Content | Reference |
|---------|---------|-----------|
| `LM_CYB_MONITORING` | Post-production vulnerability monitoring process | §8.3, §8.5 |
| `LM_CYB_INCIDENT` | Incident response procedure | §13.3 |
| `LM_CYB_UPDATE` | Software update authorization procedure | §13.4 |
| `LM_CYB_EOS` | End of cybersecurity support date and criteria | §14.3 |
| `LM_CYB_SUPPLIER` | Supplier cybersecurity capability assessment | §7.4.1 |

```rst
.. lm:: Cybersecurity monitoring: vulnerabilities tracked via
       CERT/CC and CVE databases; severity triage per CVSS v3.1.
       Critical (CVSS ≥ 9.0): respond within 7 days.
   :id: LM_CYB_MONITORING
   :tags: cybersecurity;vulnerability_monitoring;post_production
```

## UN R155 / UN R156 Evidence

OSQAr qualification shipments serve as evidence for UN regulation compliance:

| UN R155 Requirement | OSQAr Evidence |
|--------------------|----------------|
| CSMS documented | `06_lifecycle_management.rst` — organizational cybersecurity management |
| Risk assessment performed | `01_requirements.rst` — TARA-derived REQ_CYB_* needs |
| Risk treatment implemented | `02_architecture.rst` — ARCH_CYB_* mechanisms |
| Verification conducted | `03_verification.rst` — VER_CYB_* activities |
| Monitoring in place | `06_lifecycle_management.rst` — LM_CYB_MONITORING |

## Pitfalls

1. **Treating security as an afterthought** — cybersecurity must be designed in
   from concept phase (§9), not bolted on during verification.
2. **Confusing safety and security requirements** — safety addresses random
   hardware failures + systematic design errors; security addresses
   intentional malicious acts. They have different analysis methods
   (HARA vs. TARA) and different verification strategies.
3. **Over-claiming CAL** — Cybersecurity Assurance Level is NOT equivalent to
   ASIL. CAL determination uses attack potential, not severity/exposure/
   controllability.
4. **Missing post-production obligations** — ISO 21434 §13-§14 require
   continuous monitoring and incident response after SOP. OSQAr qualification
   at release time is just a snapshot.
5. **Export-controlled cryptography** — some cryptographic algorithms are
   subject to export regulations. Document which algorithms are used and
   whether they have export restrictions.
