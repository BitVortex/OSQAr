#include "osqar_shared.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
OSQAR-CODE-TRACE (test tags)

TEST: TEST_CODE_001 TEST_VERIFY_001 TEST_METHOD_001 TEST_EXEC_001 TEST_REPORT_001
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

static test_result_t test_magic_constant(void) {
    test_result_t r = {"test_magic_constant", true, {0}};

    const int got = osqar_shared_magic();
    if (got != 42) {
        char buf[256];
        snprintf(buf, sizeof(buf), "osqar_shared_magic() => %d, expected 42", got);
        set_fail(&r, buf);
        return r;
    }

    return r;
}

static test_result_t test_addition(void) {
    test_result_t r = {"test_addition", true, {0}};

    const int got = osqar_shared_add(20, 22);
    if (got != 42) {
        char buf[256];
        snprintf(buf, sizeof(buf), "osqar_shared_add(20,22) => %d, expected 42", got);
        set_fail(&r, buf);
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
        "<testsuite name=\"osqar_shared_c\" tests=\"%zu\" failures=\"%zu\" errors=\"0\" skipped=\"0\" time=\"0\">\n",
        count,
        failures
    );

    for (size_t i = 0; i < count; i++) {
        fprintf(f, "  <testcase classname=\"osqar_shared_c\" name=\"%s\" time=\"0\">\n", results[i].name);
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
        test_magic_constant(),
        test_addition(),
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
