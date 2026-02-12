# OSQAr shared C library example

This example provides a tiny C library (`LIB_SHARED_C`) that is consumed by the C, C++ and Rust examples.

It exists primarily to showcase OSQAr workspace dependency closure and deduplication: multiple shipments
declare the same dependency, and the combined example workspace contains the dependency shipment only once.
