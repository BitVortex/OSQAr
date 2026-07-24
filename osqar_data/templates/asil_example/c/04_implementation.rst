Implementation Example (C)
==========================

Source inventory and build configuration for an incomplete C example targeting
ASIL D. These files demonstrate links; they are not a qualified library.

Naming convention: ``IMPL_<CATEGORY>_<NNN>``.

Source Inventory
----------------

.. impl:: Source file inventory with an ASIL target and pending coding-standard
         tailoring.
   :id: IMPL_SOURCE_INVENTORY
   :status: draft
   :tags: ASIL_D;source_inventory

   **Language:** C (C99 or C11 with no extensions)
   **Example coding-standard target:** MISRA C:2012; not demonstrated or
   enforced by this scaffold
   **Build system:** CMake ≥3.16 with reproducible build support
   **Example compiler family:** GCC or Clang; version and target are not pinned.
   Evaluate the actual use under ISO 26262-8 Clause 11 before making any
   tool-confidence or qualification claim.
   **No dynamic allocation after init** (OSQAr project policy)
   **No recursion** (OSQAr project policy)
   **One entry, one exit per function** (OSQAr project policy)

   These exact coding restrictions are conservative scaffold defaults. They
   are not attributed to ISO 26262-6 Table 7; its researched mapping is
   software-unit verification methods; the restrictions remain scaffold policy.

Build Configuration
-------------------

.. impl:: CMake build configuration for the C example targeting ASIL D.
   :id: IMPL_BUILD_CONFIG
   :status: draft
   :tags: ASIL_D;build;CMake

   **Compiler flags:**
   - ``-std=c11 -Wall -Wextra -Wpedantic -Werror``
   - ``-Wconversion -Wshadow -Wstrict-prototypes``
   - ``-fno-strict-aliasing -fstack-protector-strong``
   - ``-D_FORTIFY_SOURCE=2``
   - ``-fsanitize=address,undefined`` (debug builds)
   - ``-fprofile-arcs -ftest-coverage`` (coverage builds)

   These are example build settings, not evidence that a coding standard,
   compiler behavior, target-platform behavior, or safety objective is satisfied.
