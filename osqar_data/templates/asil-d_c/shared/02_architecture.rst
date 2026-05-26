Architecture (ISO 26262-6 §7.4 — ASIL D SEooC)
================================================

This document describes the software architectural design implementing
the software safety requirements. Per ISO 26262-6 §7.4.3, the architecture
must define static structure, dynamic behaviour, data flow, and fault
handling with freedom from interference.

Naming convention: ``ARCH_<COMPONENT>_<NNN>``.

.. note::
   Load ``iso26262-part6-software`` for ASIL-differentiated architecture
   design principles and freedom-from-interference patterns.

Static Structure
----------------

.. arch:: The component shall be organized as a set of modules with
         well-defined interfaces and explicit dependency relationships.
         Each module shall have a single responsibility and expose
         a documented API.
   :id: ARCH_MODULE_STRUCTURE
   :status: draft
   :tags: ASIL_D;static_structure;modular_design
   :links: REQ_SSR_NOMINAL_001

.. arch:: **Safety module**: The safety-related processing shall be
         isolated in a dedicated module with no dependencies on
         non-safety modules. All data exchange shall pass through
         validated interfaces.
   :id: ARCH_SAFETY_MODULE
   :status: draft
   :tags: ASIL_D;safety_isolation;freedom_from_interference
   :links: REQ_SSR_MEMORY_001

Dynamic Behaviour
-----------------

.. arch:: All safety-related functions shall execute with deterministic
         control flow: one entry, one exit per function. No recursion.
         All loops shall have statically verifiable upper bounds.
   :id: ARCH_DETERMINISTIC_FLOW
   :status: draft
   :tags: ASIL_D;deterministic;one_entry_one_exit;no_recursion
   :links: REQ_SSR_TIMING_001

Data Flow
---------

.. arch:: Data flow through the component shall be unidirectional:
         input validation → safety processing → output generation.
         Intermediate results shall not be shared between concurrent
         invocations (no static mutable state across calls).
   :id: ARCH_DATA_FLOW
   :status: draft
   :tags: ASIL_D;data_flow;no_shared_state
   :links: REQ_SSR_NOMINAL_001

Fault Handling
--------------

.. arch:: Fault detection shall use a layered approach:
         1. Defensive input validation at API boundary
         2. Internal consistency checks (assertions, invariants)
         3. Arithmetic safety wrappers (checked operations)

         Fault reaction shall return error codes to the caller.
         No fault shall result in undefined behaviour, deadlock,
         or resource leak.
   :id: ARCH_FAULT_HANDLING
   :status: draft
   :tags: ASIL_D;fault_handling;defensive_programming;layered_defense
   :links: REQ_SSR_FAULT_001;REQ_SSR_FAULT_002;REQ_SSR_FAULTREACT_001

Error Reporting Interface
--------------------------

.. arch:: The component shall provide a structured error reporting
         interface: every function returns an error code from a
         defined enumeration. Error codes shall be documented with
         cause, severity, and recommended integrator response.
   :id: ARCH_ERROR_INTERFACE
   :status: draft
   :tags: ASIL_D;error_reporting;interface
   :links: REQ_SSR_FAULTREACT_001;REQ_SSR_EXTASSUME_003

Memory Architecture
-------------------

.. arch:: All memory used by the component shall be statically
         allocated at compile time or during initialization.
         Buffer sizes shall be defined as compile-time constants.
         No heap allocation after initialization. Stack usage
         shall be bounded and verified through static analysis.
   :id: ARCH_MEMORY_STATIC
   :status: draft
   :tags: ASIL_D;static_memory;no_heap;stack_bounding
   :links: REQ_SSR_MEMORY_001;REQ_SSR_MEMORY_002
