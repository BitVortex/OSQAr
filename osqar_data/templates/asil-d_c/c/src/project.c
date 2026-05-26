/*
 * ASIL D SEooC C Library — Implementation
 *
 * Safety-related functions implementing the public API defined in project.h.
 * Follows ISO 26262-6 Table 7 guidelines for ASIL D:
 *   - No dynamic allocation after initialization
 *   - No recursion
 *   - One entry, one exit per function
 *   - Defensive programming (null checks, range checks, overflow detection)
 *   - All error paths return defined error codes
 */

#include "project.h"
#include <limits.h>
#include <string.h>

/* Module-level state (statically allocated — no dynamic memory). */
static int g_initialized = 0;
static osqar_error_t g_last_error = OSQAR_OK;

/* Maximum size for the last-error buffer. */
#define OSQAR_ERROR_BUFFER_SIZE 128
static char g_error_buffer[OSQAR_ERROR_BUFFER_SIZE];

osqar_error_t osqar_init(void) {
    /* Defensive: already-initialized is not an error, just idempotent. */
    g_initialized = 1;
    g_last_error = OSQAR_OK;
    memset(g_error_buffer, 0, sizeof(g_error_buffer));
    return OSQAR_OK;
}

void osqar_deinit(void) {
    g_initialized = 0;
    g_last_error = OSQAR_OK;
    memset(g_error_buffer, 0, sizeof(g_error_buffer));
}

/* Check if two positive integers can be added without overflow.
 * Uses the standard safe-addition pattern:
 *   if (a > INT_MAX - b) → overflow would occur.
 */
static int safe_add_would_overflow(int a, int b) {
    if (a > 0 && b > INT_MAX - a) {
        return 1;
    }
    if (a < 0 && b < INT_MIN - a) {
        return 1;
    }
    return 0;
}

/* Check if subtracting b from a would underflow.
 *   if (b > 0 && a < INT_MIN + b) → underflow would occur.
 *   if (b < 0 && a > INT_MAX + b) → overflow would occur (subtracting negative).
 */
static int safe_subtract_would_overflow(int a, int b) {
    if (b < 0 && a > INT_MAX + b) {
        return 1;
    }
    if (b > 0 && a < INT_MIN + b) {
        return 1;
    }
    return 0;
}

osqar_error_t osqar_safe_add(int a, int b, int *result) {
    /* Defensive: null pointer check (REQ_SSR_FAULT_003). */
    if (result == NULL) {
        g_last_error = OSQAR_ERROR_NULL_POINTER;
        return OSQAR_ERROR_NULL_POINTER;
    }

    /* Defensive: initialization check (REQ_SSR_INIT_001). */
    if (!g_initialized) {
        g_last_error = OSQAR_ERROR_NOT_INITIALIZED;
        return OSQAR_ERROR_NOT_INITIALIZED;
    }

    /* Arithmetic safety check (REQ_SSR_FAULT_002). */
    if (safe_add_would_overflow(a, b)) {
        g_last_error = OSQAR_ERROR_OVERFLOW;
        return OSQAR_ERROR_OVERFLOW;
    }

    *result = a + b;
    g_last_error = OSQAR_OK;
    return OSQAR_OK;
}

osqar_error_t osqar_safe_subtract(int a, int b, int *result) {
    if (result == NULL) {
        g_last_error = OSQAR_ERROR_NULL_POINTER;
        return OSQAR_ERROR_NULL_POINTER;
    }

    if (!g_initialized) {
        g_last_error = OSQAR_ERROR_NOT_INITIALIZED;
        return OSQAR_ERROR_NOT_INITIALIZED;
    }

    if (safe_subtract_would_overflow(a, b)) {
        g_last_error = OSQAR_ERROR_UNDERFLOW;
        return OSQAR_ERROR_UNDERFLOW;
    }

    *result = a - b;
    g_last_error = OSQAR_OK;
    return OSQAR_OK;
}

const char *osqar_last_error(void) {
    /* One entry, one exit: single return statement per function. */
    const char *msg;

    switch (g_last_error) {
    case OSQAR_OK:
        msg = "No error";
        break;
    case OSQAR_ERROR_NULL_POINTER:
        msg = "NULL pointer argument";
        break;
    case OSQAR_ERROR_INVALID_RANGE:
        msg = "Value out of valid range";
        break;
    case OSQAR_ERROR_OVERFLOW:
        msg = "Arithmetic overflow detected";
        break;
    case OSQAR_ERROR_UNDERFLOW:
        msg = "Arithmetic underflow detected";
        break;
    case OSQAR_ERROR_DIVISION_BY_ZERO:
        msg = "Division by zero detected";
        break;
    case OSQAR_ERROR_BUFFER_TOO_SMALL:
        msg = "Output buffer too small";
        break;
    case OSQAR_ERROR_NOT_INITIALIZED:
        msg = "Component not initialized";
        break;
    default:
        msg = "Unknown error";
        break;
    }

    return msg;
}
