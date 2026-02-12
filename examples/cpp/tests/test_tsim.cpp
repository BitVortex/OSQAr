#include "tsim.hpp"
#include "osqar_shared.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

/*
OSQAR-CODE-TRACE (test tags)

TEST: TEST_CODE_001 TEST_VERIFY_001 TEST_METHOD_001 TEST_METHOD_002 TEST_METHOD_003 TEST_CONVERSION_001 TEST_FILTER_001 TEST_THRESHOLD_001 TEST_HYSTERESIS_001 TEST_END_TO_END_001 TEST_ERROR_RECOVERY_001 TEST_FAIL_SAFE_001 TEST_EXEC_001 TEST_REPORT_001
*/

auto fail_msg(char* buf, size_t n, const char* msg) -> void {
    std::snprintf(buf, n, "%s", msg);
}

typedef struct {
    const char* name;
    bool passed;
    char message[256];
} test_result_t;

static void set_fail(test_result_t& r, const std::string& msg) {
    r.passed = false;
    std::snprintf(r.message, sizeof(r.message), "%s", msg.c_str());
}

static test_result_t test_conversion_full_range() {
    // TEST_CONVERSION_001
    test_result_t r{"test_conversion_full_range", true, {0}};

    struct Case { uint16_t adc; tsim_temp_x10_t expected; int16_t tol; };
    const std::vector<Case> cases = {
        {0u, -400, 10},
        {2048u, 425, 10},
        {4095u, 1250, 10},
    };

    for (const auto& c : cases) {
        const auto got = tsim_adc_to_temp_x10(c.adc);
        const auto diff = static_cast<int32_t>(got) - static_cast<int32_t>(c.expected);
        if (diff > c.tol || diff < -c.tol) {
            char buf[256];
            std::snprintf(buf, sizeof(buf), "ADC %u => %d, expected %d±%d", c.adc, got, c.expected, c.tol);
            set_fail(r, buf);
            return r;
        }
    }

    return r;
}

static test_result_t test_filter_noise_rejection() {
    // TEST_FILTER_001
    test_result_t r{"test_filter_noise_rejection", true, {0}};

    const std::vector<tsim_temp_x10_t> noisy = {500, 600, 450, 550, 500, 480, 520, 490};
    tsim_filter_t f;
    f.reset();

    std::vector<tsim_temp_x10_t> outputs;
    for (auto s : noisy) {
        tsim_temp_x10_t out{0};
        if (f.update(s, out)) {
            outputs.push_back(out);
        }
    }

    if (outputs.empty()) {
        set_fail(r, "Filter produced no outputs");
        return r;
    }

    for (auto o : outputs) {
        if (o < 480 || o > 520) {
            set_fail(r, "Filtered output out of expected band (480..520)");
            return r;
        }
    }

    return r;
}

static test_result_t test_threshold_and_hysteresis() {
    // TEST_THRESHOLD_001 + TEST_HYSTERESIS_001
    test_result_t r{"test_threshold_and_hysteresis", true, {0}};

    tsim_sm_t sm;
    sm.init(1000, 950);

    if (sm.state != tsim_state_t::safe) {
        set_fail(r, "Initial state must be SAFE");
        return r;
    }

    if (sm.evaluate(999) != tsim_state_t::safe) {
        set_fail(r, "Must remain SAFE at 99.9C");
        return r;
    }

    if (sm.evaluate(1000) != tsim_state_t::unsafe) {
        set_fail(r, "Must transition to UNSAFE at 100.0C");
        return r;
    }

    if (sm.evaluate(990) != tsim_state_t::unsafe) {
        set_fail(r, "Must remain UNSAFE at 99.0C due to hysteresis");
        return r;
    }

    if (sm.evaluate(950) != tsim_state_t::safe) {
        set_fail(r, "Must recover to SAFE at 95.0C");
        return r;
    }

    return r;
}

static test_result_t test_shared_magic_constant() {
    test_result_t r{"test_shared_magic_constant", true, {0}};

    const int got = osqar_shared_magic();
    if (got != 42) {
        char buf[256];
        std::snprintf(buf, sizeof(buf), "osqar_shared_magic() => %d, expected 42", got);
        set_fail(r, buf);
        return r;
    }

    return r;
}

static void write_junit(const char* path, const std::vector<test_result_t>& results) {
    FILE* f = std::fopen(path, "w");
    if (!f) {
        std::fprintf(stderr, "Failed to open %s for writing\n", path);
        std::exit(2);
    }

    size_t failures = 0;
    for (const auto& r : results) {
        if (!r.passed) failures++;
    }

    std::fprintf(f, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    std::fprintf(
        f,
        "<testsuite name=\"tsim_cpp\" tests=\"%zu\" failures=\"%zu\" errors=\"0\" skipped=\"0\" time=\"0\">\n",
        results.size(),
        failures
    );

    for (const auto& r : results) {
        std::fprintf(f, "  <testcase classname=\"tsim_cpp\" name=\"%s\" time=\"0\">\n", r.name);
        if (!r.passed) {
            const char* msg = (r.message[0] ? r.message : "failed");
            std::fprintf(f, "    <failure message=\"%s\"/>\n", msg);
        }
        std::fprintf(f, "  </testcase>\n");
    }

    std::fprintf(f, "</testsuite>\n");
    std::fclose(f);
}

int main(int argc, char** argv) {
    const char* out = (argc >= 2) ? argv[1] : "test_results.xml";

    std::vector<test_result_t> results;
    results.push_back(test_conversion_full_range());
    results.push_back(test_filter_noise_rejection());
    results.push_back(test_threshold_and_hysteresis());
    results.push_back(test_shared_magic_constant());

    write_junit(out, results);

    for (const auto& r : results) {
        if (!r.passed) {
            std::fprintf(stderr, "FAIL: %s: %s\n", r.name, r.message);
            return 1;
        }
    }

    std::printf("PASS: %zu tests\n", results.size());
    return 0;
}
