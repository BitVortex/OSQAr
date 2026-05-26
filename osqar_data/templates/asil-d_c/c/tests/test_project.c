/*
 * ASIL D SEooC C Library — Unit Tests
 *
 * Requirements-based unit tests for the safety-related component.
 * Every test case traces to a specific software safety requirement (REQ_SSR_*)
 * and exercises both nominal and error paths.
 *
 * Test naming convention: test_<requirement_id>_<scenario>
 */

#include "project.h"
#include <limits.h>
#include <stdio.h>
#include <string.h>

static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST_ASSERT(cond, msg)                                   \
    do {                                                         \
        tests_run++;                                             \
        if (!(cond)) {                                           \
            fprintf(stderr, "FAIL: %s (%s:%d)\n",               \
                    msg, __FILE__, __LINE__);                    \
            tests_failed++;                                      \
        } else {                                                 \
            tests_passed++;                                      \
        }                                                        \
    } while (0)

/* ── Initialization Tests (REQ_SSR_INIT_001, REQ_SSR_INIT_002) ── */

static void test_init_success(void) {
    osqar_error_t err = osqar_init();
    TEST_ASSERT(err == OSQAR_OK, "init returns OK on first call");
}

static void test_init_idempotent(void) {
    osqar_init();
    osqar_error_t err = osqar_init();
    TEST_ASSERT(err == OSQAR_OK, "init is idempotent");
}

static void test_not_initialized_rejected(void) {
    osqar_deinit();
    int result = 0;
    osqar_error_t err = osqar_safe_add(1, 2, &result);
    TEST_ASSERT(err == OSQAR_ERROR_NOT_INITIALIZED,
                "operation rejected when not initialized");
}

/* ── Null Pointer Tests (REQ_SSR_FAULT_003) ── */

static void test_null_pointer_rejected(void) {
    osqar_init();
    osqar_error_t err = osqar_safe_add(1, 2, NULL);
    TEST_ASSERT(err == OSQAR_ERROR_NULL_POINTER,
                "NULL pointer rejected with error code");
}

/* ── Nominal Operation Tests (REQ_SSR_NOMINAL_001) ── */

static void test_safe_add_nominal(void) {
    osqar_init();
    int result = 0;
    osqar_error_t err = osqar_safe_add(10, 20, &result);
    TEST_ASSERT(err == OSQAR_OK, "safe_add returns OK for valid inputs");
    TEST_ASSERT(result == 30, "safe_add computes correct result");
}

static void test_safe_add_negative(void) {
    int result = 0;
    osqar_error_t err = osqar_safe_add(-5, -10, &result);
    TEST_ASSERT(err == OSQAR_OK, "safe_add handles negative numbers");
    TEST_ASSERT(result == -15, "safe_add computes correct negative result");
}

static void test_safe_add_zero(void) {
    int result = 0;
    osqar_error_t err = osqar_safe_add(0, 42, &result);
    TEST_ASSERT(err == OSQAR_OK, "safe_add handles zero operand");
    TEST_ASSERT(result == 42, "safe_add with zero is identity");
}

static void test_safe_subtract_nominal(void) {
    int result = 0;
    osqar_error_t err = osqar_safe_subtract(50, 20, &result);
    TEST_ASSERT(err == OSQAR_OK, "safe_subtract returns OK for valid inputs");
    TEST_ASSERT(result == 30, "safe_subtract computes correct result");
}

/* ── Arithmetic Safety Tests (REQ_SSR_FAULT_002) ── */

static void test_overflow_detected(void) {
    osqar_init();
    int result = 0;
    osqar_error_t err = osqar_safe_add(INT_MAX, 1, &result);
    TEST_ASSERT(err == OSQAR_ERROR_OVERFLOW,
                "overflow detected for INT_MAX + 1");
}

static void test_underflow_detected(void) {
    osqar_init();
    int result = 0;
    osqar_error_t err = osqar_safe_add(INT_MIN, -1, &result);
    TEST_ASSERT(err == OSQAR_ERROR_OVERFLOW,
                "underflow detected for INT_MIN + (-1)");
}

static void test_subtract_underflow_detected(void) {
    osqar_init();
    int result = 0;
    osqar_error_t err = osqar_safe_subtract(INT_MIN, 1, &result);
    TEST_ASSERT(err == OSQAR_ERROR_UNDERFLOW,
                "underflow detected for INT_MIN - 1");
}

/* ── Boundary Tests ── */

static void test_overflow_boundary_safe(void) {
    osqar_init();
    int result = 0;
    /* INT_MAX + (-1) should not overflow. */
    osqar_error_t err = osqar_safe_add(INT_MAX, -1, &result);
    TEST_ASSERT(err == OSQAR_OK,
                "INT_MAX + (-1) does not overflow");
    TEST_ASSERT(result == INT_MAX - 1,
                "INT_MAX + (-1) computes correctly");
}

static void test_underflow_boundary_safe(void) {
    osqar_init();
    int result = 0;
    /* INT_MIN + 1 should not underflow. */
    osqar_error_t err = osqar_safe_add(INT_MIN, 1, &result);
    TEST_ASSERT(err == OSQAR_OK,
                "INT_MIN + 1 does not underflow");
    TEST_ASSERT(result == INT_MIN + 1,
                "INT_MIN + 1 computes correctly");
}

/* ── Error Reporting Tests (REQ_SSR_FAULTREACT_001) ── */

static void test_last_error_stores(void) {
    osqar_init();
    int result = 0;
    osqar_safe_add(1, 2, NULL); /* Triggers NULL pointer error */
    const char *msg = osqar_last_error();
    TEST_ASSERT(strstr(msg, "NULL pointer") != NULL,
                "last_error reports the correct error");
}

static void test_last_error_clears_on_success(void) {
    osqar_init();
    int result = 0;
    /* Trigger an error */
    osqar_safe_add(1, 2, NULL);
    /* Then a successful operation should clear it */
    osqar_safe_add(1, 2, &result);
    const char *msg = osqar_last_error();
    TEST_ASSERT(strcmp(msg, "No error") == 0,
                "last_error cleared after successful operation");
}

/* ── Test Runner ── */

int main(void) {
    /* Initialization */
    test_init_success();
    test_init_idempotent();
    test_not_initialized_rejected();

    /* Null pointer defense */
    test_null_pointer_rejected();

    /* Nominal operations */
    test_safe_add_nominal();
    test_safe_add_negative();
    test_safe_add_zero();
    test_safe_subtract_nominal();

    /* Arithmetic safety */
    test_overflow_detected();
    test_underflow_detected();
    test_subtract_underflow_detected();

    /* Boundary conditions */
    test_overflow_boundary_safe();
    test_underflow_boundary_safe();

    /* Error reporting */
    test_last_error_stores();
    test_last_error_clears_on_success();

    /* Summary */
    printf("Tests: %d run, %d passed, %d failed\n",
           tests_run, tests_passed, tests_failed);

    return tests_failed > 0 ? 1 : 0;
}
