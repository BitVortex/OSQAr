Requirements (ISO 26262-6 §6.4 — ASIL D SEooC)
===================================================

This document specifies the software safety requirements (SSRs) derived from
the Technical Safety Requirements (TSRs) allocated to software for this
ASIL D SEooC qualification attempt.

Naming convention: ``REQ_SSR_<CATEGORY>_<NNN>`` where categories are:
``NOMINAL``, ``FAULT``, ``INIT``, ``SHUTDOWN``, ``INTERFACE``, ``TIMING``,
``MONITOR``, ``MEMORY``, ``REDUNDANCY``, ``DIAG``, ``CONFIG``, ``EXTASSUME``.

.. note::
   This template follows :ref:`ISO 26262-6 §6.4.1 <iso-26262-6-6.4.1>` for
   software safety requirements specification. Load ``iso26262-part6-software``
   for ASIL-differentiated guidance on authoring these needs.

Nominal Operation
-----------------

.. need:: The component shall provide a safe, documented interface for
          <INSERT FUNCTIONALITY> with input validation, error reporting,
          and deterministic resource usage.
   :id: REQ_SSR_NOMINAL_001
   :status: draft
   :tags: ASIL_D;nominal;safe_interface

.. need:: All external inputs shall be validated for range, type, and
          structural integrity before any safety-related processing.
   :id: REQ_SSR_NOMINAL_002
   :status: draft
   :tags: ASIL_D;input_validation;defensive_programming

Fault Detection
---------------

.. need:: The component shall detect invalid input values and return
          a defined error code without undefined behaviour.
   :id: REQ_SSR_FAULT_001
   :status: draft
   :tags: ASIL_D;fault_detection;error_handling

.. need:: The component shall detect arithmetic overflow, underflow,
          and division-by-zero conditions in safety-related computations.
   :id: REQ_SSR_FAULT_002
   :status: draft
   :tags: ASIL_D;fault_detection;arithmetic_safety

.. need:: The component shall detect NULL pointer dereference attempts
          on all externally-exposed API functions.
   :id: REQ_SSR_FAULT_003
   :status: draft
   :tags: ASIL_D;fault_detection;null_pointer;defensive_programming

Fault Reaction
--------------

.. need:: Upon fault detection, the component shall transition to a
          safe state (return error, no partial writes, no memory leaks)
          and log the fault condition via the error reporting interface.
   :id: REQ_SSR_FAULTREACT_001
   :status: draft
   :tags: ASIL_D;fault_reaction;safe_state

Initialization
--------------

.. need:: The component shall initialize all internal state to known
          safe values before any safety-related function may be called.
   :id: REQ_SSR_INIT_001
   :status: draft
   :tags: ASIL_D;initialization;safe_state

.. need:: The component shall provide an initialization function that
          returns a status code indicating success or the specific
          initialization failure cause.
   :id: REQ_SSR_INIT_002
   :status: draft
   :tags: ASIL_D;initialization;error_reporting

Timing Constraints
------------------

.. need:: All safety-related functions shall have bounded worst-case
          execution time (WCET), free of unbounded loops and recursion.
   :id: REQ_SSR_TIMING_001
   :status: draft
   :tags: ASIL_D;timing;WCET;no_recursion

Memory Safety
-------------

.. need:: The component shall not use dynamic memory allocation (malloc,
          calloc, realloc, free) after initialization. All memory shall
          be statically allocated or allocated during init only.
   :id: REQ_SSR_MEMORY_001
   :status: draft
   :tags: ASIL_D;memory_safety;no_dynamic_allocation

.. need:: All statically-allocated buffers shall have defined maximum
          sizes and all access shall be bounds-checked.
   :id: REQ_SSR_MEMORY_002
   :status: draft
   :tags: ASIL_D;memory_safety;bounds_checking

Interface Validation
--------------------

.. need:: All data crossing the component boundary shall be validated
          for integrity before use in safety-related processing.
   :id: REQ_SSR_INTERFACE_001
   :status: draft
   :tags: ASIL_D;interface_validation;data_integrity

Assumptions of Use (SEooC — ISO 26262-10 §9.4.2)
--------------------------------------------------

.. need:: **Integration context**: The component assumes single-threaded
          execution or externally-synchronized multi-threaded access.
          The integrator is responsible for thread safety if used in
          a concurrent context.
   :id: REQ_SSR_EXTASSUME_001
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;integration

.. need:: **Input constraints**: All input data is assumed to be
          pre-validated by hardware diagnostics or a higher-level
          safety mechanism for physical integrity (CRC, E2E).
          The component validates logical integrity (range, type).
   :id: REQ_SSR_EXTASSUME_002
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;input_validation

.. need:: **Error handling**: The integrator shall provide an error
          handling policy that defines the system-level response to
          each fault code returned by the component.
   :id: REQ_SSR_EXTASSUME_003
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;error_handling

.. need:: **Toolchain**: The component shall be built with a qualified
          compiler (TCL3 per ISO 26262-8 §11.4) and linked against
          a qualified C runtime library.
   :id: REQ_SSR_EXTASSUME_004
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;toolchain

.. need:: **Build reproducibility**: The component shall produce bit-
          identical binaries across rebuilds when SOURCE_DATE_EPOCH is set.
   :id: REQ_SSR_EXTASSUME_005
   :status: draft
   :tags: ASIL_D;SEooC;assumption_of_use;reproducible_build
