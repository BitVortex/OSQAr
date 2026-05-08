#ifndef OSQAR_SHARED_H
#define OSQAR_SHARED_H

#ifdef __cplusplus
extern "C" {
#endif

// A tiny shared library used across OSQAr examples.
//
// This is intentionally small: it exists to demonstrate how multiple
// OSQAr-annotated projects can depend on the same annotated library.

int osqar_shared_magic(void);
int osqar_shared_add(int a, int b);

#ifdef __cplusplus
}
#endif

#endif
