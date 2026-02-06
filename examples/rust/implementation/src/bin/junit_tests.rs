use std::env;
use std::fs::File;
use std::io::{self, Write};

use tsim::{adc_to_temp_x10, Filter, StateMachine, State};

// OSQAR-CODE-TRACE (test tags)
//
// TEST: TEST_CODE_001 TEST_VERIFY_001 TEST_METHOD_001 TEST_METHOD_002 TEST_METHOD_003 TEST_CONVERSION_001 TEST_FILTER_001 TEST_THRESHOLD_001 TEST_HYSTERESIS_001 TEST_END_TO_END_001 TEST_ERROR_RECOVERY_001 TEST_FAIL_SAFE_001 TEST_EXEC_001 TEST_REPORT_001

#[derive(Debug)]
struct TestResult {
    name: &'static str,
    passed: bool,
    message: String,
}

fn pass(name: &'static str) -> TestResult {
    TestResult { name, passed: true, message: String::new() }
}

fn fail(name: &'static str, message: impl Into<String>) -> TestResult {
    TestResult { name, passed: false, message: message.into() }
}

fn test_conversion_full_range() -> TestResult {
    // TEST_CONVERSION_001
    let cases = [
        (0u16, -400i16, 10i16),
        (2048u16, 425i16, 10i16),
        (4095u16, 1250i16, 10i16),
    ];

    for (adc, expected, tol) in cases {
        let got = adc_to_temp_x10(adc);
        let diff = got as i32 - expected as i32;
        if diff > tol as i32 || diff < -(tol as i32) {
            return fail(
                "test_conversion_full_range",
                format!("ADC {adc} => {got}, expected {expected}±{tol}"),
            );
        }
    }

    pass("test_conversion_full_range")
}

fn test_filter_noise_rejection() -> TestResult {
    // TEST_FILTER_001
    let noisy: [i16; 8] = [500, 600, 450, 550, 500, 480, 520, 490];
    let mut filter = Filter::new();

    let mut outputs: Vec<i16> = Vec::new();
    for s in noisy {
        if let Some(out) = filter.update(s) {
            outputs.push(out);
        }
    }

    if outputs.is_empty() {
        return fail("test_filter_noise_rejection", "Filter produced no outputs");
    }

    for o in outputs {
        if o < 480 || o > 520 {
            return fail("test_filter_noise_rejection", "Filtered output out of expected band (480..520)");
        }
    }

    pass("test_filter_noise_rejection")
}

fn test_threshold_and_hysteresis() -> TestResult {
    // TEST_THRESHOLD_001 + TEST_HYSTERESIS_001
    let mut sm = StateMachine::new(1000, 950);

    if sm.state != State::Safe {
        return fail("test_threshold_and_hysteresis", "Initial state must be SAFE");
    }

    if sm.evaluate(999) != State::Safe {
        return fail("test_threshold_and_hysteresis", "Must remain SAFE at 99.9C");
    }

    if sm.evaluate(1000) != State::Unsafe {
        return fail("test_threshold_and_hysteresis", "Must transition to UNSAFE at 100.0C");
    }

    if sm.evaluate(990) != State::Unsafe {
        return fail("test_threshold_and_hysteresis", "Must remain UNSAFE at 99.0C due to hysteresis");
    }

    if sm.evaluate(950) != State::Safe {
        return fail("test_threshold_and_hysteresis", "Must recover to SAFE at 95.0C");
    }

    pass("test_threshold_and_hysteresis")
}

fn write_junit(mut w: impl Write, suite: &str, results: &[TestResult]) -> io::Result<()> {
    let failures = results.iter().filter(|r| !r.passed).count();

    writeln!(w, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>")?;
    writeln!(
        w,
        "<testsuite name=\"{}\" tests=\"{}\" failures=\"{}\" errors=\"0\" skipped=\"0\" time=\"0\">",
        suite,
        results.len(),
        failures
    )?;

    for r in results {
        writeln!(
            w,
            "  <testcase classname=\"{}\" name=\"{}\" time=\"0\">",
            suite,
            r.name
        )?;
        if !r.passed {
            let msg = if r.message.is_empty() { "failed" } else { r.message.as_str() };
            writeln!(w, "    <failure message=\"{}\"/>", xml_escape(msg))?;
        }
        writeln!(w, "  </testcase>")?;
    }

    writeln!(w, "</testsuite>")?;
    Ok(())
}

fn xml_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&apos;")
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let out = args.get(1).map(|s| s.as_str()).unwrap_or("test_results.xml");

    let results = vec![
        test_conversion_full_range(),
        test_filter_noise_rejection(),
        test_threshold_and_hysteresis(),
    ];

    let mut file = File::create(out).expect("failed to open output file");
    write_junit(&mut file, "tsim_rust", &results).expect("failed to write JUnit");

    for r in &results {
        if !r.passed {
            eprintln!("FAIL: {}: {}", r.name, r.message);
            std::process::exit(1);
        }
    }

    println!("PASS: {} tests", results.len());
}
