#pragma once

/*
 * C example targeting ASIL D — Public API
 *
 * This header defines the public interface of the safety-related
 * component. All functions follow the SEooC error-reporting pattern:
 * return an error code, accept validated inputs, and operate with
 * deterministic resource usage (no dynamic allocation, no recursion).
 *
 * ISO 26262-6:2018, Clause 8.4, Table 6 provides the software-unit
 * design and implementation context. The concrete restrictions below are
 * OSQAr template policy and require project tailoring; they are not direct
 * ISO 26262 mandates.
 */

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>

/* Error codes returned by all safety-related functions. */
typedef enum {
    OSQAR_OK = 0,
    OSQAR_ERROR_NULL_POINTER = 1,
    OSQAR_ERROR_INVALID_RANGE = 2,
    OSQAR_ERROR_OVERFLOW = 3,
    OSQAR_ERROR_UNDERFLOW = 4,
    OSQAR_ERROR_DIVISION_BY_ZERO = 5,
    OSQAR_ERROR_BUFFER_TOO_SMALL = 6,
    OSQAR_ERROR_NOT_INITIALIZED = 7,
    OSQAR_ERROR_INTERNAL = 99,
} osqar_error_t;

/**
 * Initialize the component. Must be called once before any other function.
 *
 * @return OSQAR_OK on success, error code on failure.
 */
osqar_error_t osqar_init(void);

/**
 * De-initialize the component. Releases any resources acquired during init.
 * After calling deinit, init must be called again before any other function.
 */
void osqar_deinit(void);

/**
 * Example safety-related function: safe addition with overflow detection.
 *
 * @param a     First operand (validated internally)
 * @param b     Second operand (validated internally)
 * @param[out] result  Pointer to store the result (must not be NULL)
 * @return OSQAR_OK on success, OSQAR_ERROR_NULL_POINTER if result is NULL,
 *         OSQAR_ERROR_OVERFLOW if the addition would overflow.
 */
osqar_error_t osqar_safe_add(int a, int b, int *result);

/**
 * Example safety-related function: safe subtraction with underflow detection.
 *
 * @param a     First operand (validated internally)
 * @param b     Second operand (validated internally)
 * @param[out] result  Pointer to store the result (must not be NULL)
 * @return OSQAR_OK on success, OSQAR_ERROR_NULL_POINTER if result is NULL,
 *         OSQAR_ERROR_UNDERFLOW if the subtraction would underflow.
 */
osqar_error_t osqar_safe_subtract(int a, int b, int *result);

/**
 * Retrieve the last error description as a human-readable string.
 *
 * @return Static string describing the last error (always valid).
 */
const char *osqar_last_error(void);

#ifdef __cplusplus
}
#endif
