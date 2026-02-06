Implementation
==============

This scaffold intentionally keeps the implementation minimal.

Tracing into source files
========================

OSQAr’s traceability chain can include **implementation and test code** by:

- creating code-level needs (e.g., ``CODE_*``) and linking them to ``REQ_*``, ``ARCH_*``, and ``TEST_*``
- embedding excerpts via ``literalinclude`` (so the shipped HTML contains the evidence)
- attaching full source files via ``:download:`` (so reviewers can inspect complete context)

Example (adapt the file paths and links):

.. need:: (CODE) Implementation traced into sources.
    :id: CODE_IMPL_001
    :status: active
    :tags: implementation, code
    :links: REQ_001, ARCH_001, TEST_001

    - :download:`src/<your_module>.c <src/your_module.c>`
    - :download:`tests/test_<your_module>.c <tests/test_your_module.c>`

    .. literalinclude:: src/your_module.c
        :language: c

Typical starting layout:

- ``src/``: implementation sources
- ``tests/``: tests
- ``include/``: public headers (common for C/C++)

Replace the placeholder code with your real component implementation and keep the docs and trace links up to date.
