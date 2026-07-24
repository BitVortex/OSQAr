Implementation Example (Rust)
=============================

This page inventories the Rust implementation included only to demonstrate how
project needs can link to source and build configuration. It is not a qualified
library and its presence does not establish ASIL capability.

Source inventory
----------------

.. impl:: Rust source and unit-test inventory for the example component.
   :id: IMPL_SOURCE_INVENTORY
   :status: draft
   :tags: ASIL_D;source_inventory;rust;example

   **Language:** Rust (edition 2021)
   **Coding guidance:** Project-selected Rust safety and style rules, pending
   **Build system:** Cargo
   **Compiler:** Project-pinned Rust toolchain, pending reviewed tool-use analysis
   **Allocation policy:** No heap allocation in the example arithmetic component

Build configuration
-------------------

.. impl:: Cargo build configuration for the Rust example targeting ASIL D.
   :id: IMPL_BUILD_CONFIG
   :status: draft
   :tags: ASIL_D;build;cargo;rust;example

   ``Cargo.toml`` declares a library crate. ``cargo test --all-targets`` exercises
   the checked-arithmetic API. A real project must pin its toolchain, target,
   compiler options, dependency policy, and reproducibility controls, then assess
   relied-upon tool uses for the actual context.
