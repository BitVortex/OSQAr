#include "tsim.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
OSQAR-CODE-TRACE (test tags)

TEST: TEST_CODE_001 TEST_VERIFY_001 TEST_METHOD_001 TEST_METHOD_002 TEST_METHOD_003 TEST_CONVERSION_001 TEST_FILTER_001 TEST_THRESHOLD_001 TEST_HYSTERESIS_001 TEST_END_TO_END_001 TEST_ERROR_RECOVERY_001 TEST_FAIL_SAFE_001 TEST_EXEC_001 TEST_REPORT_001
*/

typedef struct {
    const char* name;
    bool passed;
    char message[256];
} test_result_t;

static void set_fail(test_result_t* r, const char* msg) {
    r->passed = false;
    strncpy(r->message, msg, sizeof(r->message) - 1);
    r->message[sizeof(r->message) - 1] = '\0';
}

static test_result_t test_conversion_full_range(void) {
    // TEST_CONVERSION_001
    test_result_t r = {"test_conversion_full_range", true, {0}};

    struct { uint16_t adc; tsim_temp_x10_t expected; int16_t tol; } cases[] = {
        {0u, -400, 10},
        {2048u, 425, 10},
        {4095u, 1250, 10},
    };

    for (size_t i = 0; i < sizeof(cases)/sizeof(cases[0]); i++) {
        const tsim_temp_x10_t got = tsim_adc_to_temp_x10(cases[i].adc);
        const int32_t diff = (int32_t)got - (int32_t)cases[i].expected;
        if (diff > cases[i].tol || diff < -cases[i].tol) {
            char buf[256];
            snprintf(buf, sizeof(buf), "ADC %u => %d, expected %d±%d", cases[i].adc, got, cases[i].expected, cases[i].tol);
            set_fail(&r, buf);
            return r;
        }
    }

    return r;
}

static test_result_t test_filter_noise_rejection(void) {
    // TEST_FILTER_001
    test_result_t r = {"test_filter_noise_rejection", true, {0}};

    const tsim_temp_x10_t noisy[] = {500, 600, 450, 550, 500, 480, 520, 490};
    tsim_filter_t f;
    tsim_filter_init(&f);

    tsim_temp_x10_t outputs[16];
    size_t out_count = 0;

    for (size_t i = 0; i < sizeof(noisy)/sizeof(noisy[0]); i++) {
        tsim_temp_x10_t out;
        if (tsim_filter_update(&f, noisy[i], &out)) {
            outputs[out_count++] = out;
        }
    }

    if (out_count < 1) {
        set_fail(&r, "Filter produced no outputs");
        return r;
    }

    // outputs should be near nominal 500
    for (size_t i = 0; i < out_count; i++) {
        if (outputs[i] < 480 || outputs[i] > 520) {
            set_fail(&r, "Filtered output out of expected band (480..520)");
            return r;
        }
    }

    return r;
}

static test_result_t test_threshold_and_hysteresis(void) {
    // TEST_THRESHOLD_001 + TEST_HYSTERESIS_001
    test_result_t r = {"test_threshold_and_hysteresis", true, {0}};

    tsim_sm_t sm;
    tsim_sm_init(&sm, 1000, 950);

    if (sm.state != TSIM_STATE_SAFE) {
        set_fail(&r, "Initial state must be SAFE");
        return r;
    }

    if (tsim_sm_evaluate(&sm, 999) != TSIM_STATE_SAFE) {
        set_fail(&r, "Must remain SAFE at 99.9C");
        return r;
    }

    if (tsim_sm_evaluate(&sm, 1000) != TSIM_STATE_UNSAFE) {
        set_fail(&r, "Must transition to UNSAFE at 100.0C");
        return r;
    }

    if (tsim_sm_evaluate(&sm, 990) != TSIM_STATE_UNSAFE) {
        set_fail(&r, "Must remain UNSAFE at 99.0C due to hysteresis");
        return r;
    }

    if (tsim_sm_evaluate(&sm, 950) != TSIM_STATE_SAFE) {
        set_fail(&r, "Must recover to SAFE at 95.0C");
        return r;
    }

    return r;
}

static void write_junit(const char* path, const test_result_t* results, size_t count) {
    FILE* f = fopen(path, "w");
    if (!f) {
        fprintf(stderr, "Failed to open %s for writing\n", path);
        exit(2);
    }

    size_t failures = 0;
    for (size_t i = 0; i < count; i++) {
        if (!results[i].passed) failures++;
    }

    fprintf(f, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    fprintf(
        f,
        "<testsuite name=\"tsim_c\" tests=\"%zu\" failures=\"%zu\" errors=\"0\" skipped=\"0\" time=\"0\">\n",
        count,
        failures
    );

    for (size_t i = 0; i < count; i++) {
        fprintf(f, "  <testcase classname=\"tsim_c\" name=\"%s\" time=\"0\">\n", results[i].name);
        if (!results[i].passed) {
            fprintf(f, "    <failure message=\"%s\"/>\n", results[i].message[0] ? results[i].message : "failed");
        }
        fprintf(f, "  </testcase>\n");
    }

    fprintf(f, "</testsuite>\n");
    fclose(f);
}

int main(int argc, char** argv) {
    const char* out = (argc >= 2) ? argv[1] : "test_results.xml";

    test_result_t results[] = {
        test_conversion_full_range(),
        test_filter_noise_rejection(),
        test_threshold_and_hysteresis(),
    };

    const size_t count = sizeof(results)/sizeof(results[0]);
    write_junit(out, results, count);

    for (size_t i = 0; i < count; i++) {
        if (!results[i].passed) {
            fprintf(stderr, "FAIL: %s: %s\n", results[i].name, results[i].message);
            return 1;
        }
    }

    printf("PASS: %zu tests\n", count);
    return 0;
}
