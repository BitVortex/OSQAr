# OSQAr Skills — Disclaimer

**These skills are experimental guidance for OSQAr qualification workflows. They are NOT normative, NOT certified, and NOT a substitute for professional functional safety engineering.**

## LLM Usage in Qualification and Compliance Work

These skills are designed to be used with large language models (LLMs) to assist in authoring qualification artifacts. **Using LLMs in functional safety, cybersecurity, or compliance contexts carries substantial risks, including but not limited to:**

- **Hallucinated clause references** — LLMs may invent standard clauses, requirement numbers, or acceptance criteria that do not exist in the published standards. Every clause reference must be independently verified against the actual standard.
- **Overconfident incorrect answers** — LLMs present incorrect information with the same confidence as correct information. Safety-critical errors may not be obvious.
- **Missing context** — LLMs do not understand the specific integration context, operational design domain, or supply chain constraints of a real vehicle program. Generic advice may be dangerously inappropriate for a specific application.
- **Incomplete coverage** — LLMs may omit safety requirements, verification activities, or lifecycle phases that are mandatory for the target ASIL/CAL. Gaps in qualification are not always visible.
- **Outdated knowledge** — standards are revised periodically. An LLM's knowledge cutoff may precede the current edition of a referenced standard.
- **No accountability** — an LLM cannot sign a safety case, cannot testify in an assessment, and cannot be held legally responsible for safety decisions.

## Human Responsibility

**Responsibility for all qualification artifacts, safety decisions, and compliance claims can only be claimed by humans.** Specifically:

- Every requirement must be reviewed and approved by a competent functional safety engineer.
- Every verification result must be traceable to an automated tool run executed by a human operator.
- Every safety case argument must be owned by a named safety manager with the authority to accept residual risk.
- Every compliance claim must be verified by an independent assessor per the applicable standard's confirmation measure requirements.

No LLM output, regardless of how plausible or authoritative it appears, may be accepted into a qualification baseline without human review. The LLM is a drafting assistant, not an engineer.

## Skill Ecosystem

OSQAr ships two categories of skills, with a third category reserved for
organization-internal use:

1. **Content-Authoring Skills** (in this directory): Map ISO standards to OSQAr need types with ASIL-differentiated guidance and RST examples. These are public-safe and shipped with the OSQAr repository. See ``SKILL_INDEX.md`` for the complete catalogue.

2. **Domain-Specific Skills** (external, agent profile): Provide deep domain expertise — clause-level requirements, hazard analysis methods, cross-standard navigation — recommended for standards compliance work. These are part of the Hermes Agent research profile and are NOT shipped with OSQAr. Agents assisting with qualification should load both content-authoring and domain-specific skills. See ``docs/agent_skills_usage.rst`` (in the OSQAr documentation) for guidance on navigating the full skill ecosystem.

3. **Organization-Specific Skills** (not shipped): Internal working guidelines, process templates, toolchain conventions, review checklists. These are maintained by individual organizations in their own repositories and are never committed to the public OSQAr repository.

## Experimental Status

These skills are provided for **experimental use only**. They have not been validated against any formal qualification, have not been reviewed by an accredited functional safety assessor, and make no claims of fitness for any particular purpose. Use them at your own risk and in compliance with your organization's tool qualification and process requirements.

## Standards References

These skills reference ISO 26262, ISO/SAE 21434, ISO 21448, and UN regulations by clause number and title only. They do not reproduce verbatim standard text. Compliance with any standard requires access to and understanding of the full published standard, not just the clause references in these skills.

---

*OSQAr is an open-source qualification architecture tool. These skills are community contributions and do not represent the official position of any standards body, regulatory authority, or certification organization.*
