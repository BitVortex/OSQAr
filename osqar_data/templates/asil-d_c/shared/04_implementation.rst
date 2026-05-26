Implementation (ISO 26262-6 §8.4 — ASIL D)
===========================================

Source inventory, build configuration, and implementation-level artifacts
for the ASIL D SEooC qualification attempt.

Naming convention: ``IMPL_<CATEGORY>_<NNN>``.

Source Inventory
----------------

.. impl:: Source file inventory with ASIL classification and
         coding standard compliance status.
   :id: IMPL_SOURCE_INVENTORY
   :status: draft
   :tags: ASIL_D;source_inventory

   **Language:** C (C99 or C11 with no extensions)
   **Coding standard:** MISRA C:2012 (mandatory rules enforced)
   **Build system:** CMake ≥3.16 with reproducible build support
   **Compiler:** GCC ≥10 or Clang ≥14 (qualified per ISO 26262-8 §11)
   **No dynamic allocation after init** (ISO 26262-6 Table 7: ++ for ASIL D)
   **No recursion** (ISO 26262-6 Table 7: ++ for ASIL C/D)
   **One entry, one exit per function** (ISO 26262-6 Table 7: ++ for all ASIL)

Build Configuration
-------------------

.. impl:: Build configuration for ASIL D C library targeting
         safety-related systems.
   :id: IMPL_BUILD_CONFIG
   :status: draft
   :tags: ASIL_D;build;CMake

   **Compiler flags:**
   - ``-std=c11 -Wall -Wextra -Wpedantic -Werror``
   - ``-Wconversion -Wshadow -Wstrict-prototypes``
   - ``-fno-strict-aliasing -fstack-protector-strong``
   - ``-D_FORTIFY_SOURCE=2 -O2``
   - ``-fsanitize=address,undefined`` (debug builds)
   - ``-fprofile-arcs -ftest-coverage`` (coverage builds)

   **Linker flags:**
   - ``-Wl,-z,relro -Wl,-z,now`` (full RELRO)
   - ``-fsanitize=address,undefined`` (debug builds)
