from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import tools.framework_test_report as framework_test_report
from tools.framework_test_report import FrameworkReportError, cli, validate_junit_report
from tools.osqar_evidence import _junit_rejection


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "report.xml"
    path.write_text(body, encoding="utf-8")
    return path


def _ci_command(report: Path, json_report: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "tools.framework_test_report", str(report)]
    if json_report is not None:
        command.extend(["--json-report", str(json_report)])
    return subprocess.run(command, text=True, capture_output=True, check=False)


def _nested_junit(depth: int) -> str:
    openings: list[str] = []
    closings: list[str] = []
    for level in range(depth):
        tag = "testsuite" if level % 2 == 0 or level == depth - 1 else "testsuites"
        openings.append(
            f"<{tag} tests='1' failures='0' errors='0' skipped='0'>"
        )
        closings.append(f"</{tag}>")
    return "".join(openings) + "<testcase name='pass'/>" + "".join(reversed(closings))


VALID_NESTED = (
    "<testsuites tests='2' failures='0' errors='0' skipped='0'>"
    "<testsuite tests='2' failures='0' errors='0' skipped='0'>"
    "<testcase name='outer-pass'/>"
    "<testsuites tests='1' failures='0' errors='0' skipped='0'>"
    "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
    "<testcase name='nested-pass'/></testsuite></testsuites>"
    "</testsuite></testsuites>"
)

STALE_PASS = '{"schema":"osqar.framework-test-report.v1","status":"PASS","tests":99}\n'

JUNIT_CLOSED_GRAMMAR_REJECTIONS = [
    pytest.param(
        "<testsuite tests='1'><testcase name='outer'><testsuite tests='1'>"
        "<testcase name='hidden'/></testsuite></testcase></testsuite>",
        "malformed JUnit structure: testcase contains nested testsuite",
        id="suite-beneath-testcase",
    ),
    pytest.param(
        "<testsuite tests='1'><testcase name='outer'><wrapper>"
        "<testsuites tests='1'><testsuite tests='1'><testcase name='hidden'/>"
        "</testsuite></testsuites></wrapper></testcase></testsuite>",
        "malformed JUnit structure: testcase contains nested testsuites",
        id="wrapped-container-beneath-testcase",
    ),
    pytest.param(
        "<testsuite tests='1'><testcase name='outer'><testcase name='nested'/>"
        "</testcase></testsuite>",
        "malformed JUnit structure: testcase contains nested testcase",
        id="testcase-beneath-testcase",
    ),
    pytest.param(
        "<testsuite xmlns='urn:junit' tests='1'><testcase xmlns='' name='pass'/>"
        "</testsuite>",
        "malformed JUnit namespace: recognized element 'testcase' uses namespace "
        "<none>; expected 'urn:junit'",
        id="namespaced-root-unnamespaced-case",
    ),
    pytest.param(
        "<testsuite tests='1' failures='1'><testcase name='failed'>"
        "<failure xmlns='urn:junit'/></testcase></testsuite>",
        "malformed JUnit namespace: recognized element 'failure' uses namespace "
        "'urn:junit'; expected <none>",
        id="unnamespaced-root-namespaced-outcome",
    ),
    pytest.param(
        "<testsuite xmlns='urn:junit' tests='1' failures='1'>"
        "<testcase name='failed'><failure xmlns='urn:other'/></testcase></testsuite>",
        "malformed JUnit namespace: recognized element 'failure' uses namespace "
        "'urn:other'; expected 'urn:junit'",
        id="mixed-recognized-namespaces",
    ),
    pytest.param(
        "<testsuite tests='1' failures='1'><testcase name='failed'>"
        "<wrapper><failure/></wrapper></testcase></testsuite>",
        "malformed JUnit structure: outcome elements must be direct children of testcase",
        id="wrapped-outcome-beneath-testcase",
    ),
    pytest.param(
        "<testsuite tests='1' failures='1'><testcase name='failed'>"
        "<failure/><failure/></testcase></testsuite>",
        "malformed JUnit testcase outcomes: multiple outcome elements",
        id="duplicate-outcome",
    ),
    pytest.param(
        "<testsuite tests='1' failures='1' errors='1'><testcase name='failed'>"
        "<failure/><error/></testcase></testsuite>",
        "malformed JUnit testcase outcomes: multiple outcome elements",
        id="mixed-outcomes",
    ),
]

INVALID_COUNTER_SPELLINGS = [
    pytest.param("+1", id="leading-plus"),
    pytest.param("1_0", id="underscore"),
    pytest.param(" 1", id="leading-whitespace"),
    pytest.param("1 ", id="trailing-whitespace"),
    pytest.param("١", id="non-ascii-digit"),
    pytest.param("01", id="leading-zero"),
    pytest.param("1.0", id="float"),
    pytest.param("1e0", id="scientific-notation"),
    pytest.param("9" * 5000, id="excessive-digit-count"),
]

STALE_INVALID_REPORTS = [
    pytest.param(None, "not found", id="missing-report"),
    pytest.param("<testsuite>", "malformed JUnit report", id="malformed-xml"),
    pytest.param(
        "<testsuite tests='1' failures='1' errors='0' skipped='0'>"
        "<testcase name='failed'><failure/></testcase></testsuite>",
        "framework tests failed",
        id="failed-report",
    ),
    pytest.param(
        "<testsuite tests='1' failures='0' errors='0' skipped='1'>"
        "<testcase name='skipped'><skipped/></testcase></testsuite>",
        "required framework tests were skipped",
        id="skipped-report",
    ),
    pytest.param(
        "<testsuites tests='0' failures='0' errors='0' skipped='0'/>",
        "zero executed tests",
        id="zero-test-report",
    ),
    pytest.param(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='visible-pass'/><failure>hidden crash</failure>"
        "</testsuite>",
        "outcome elements outside testcase",
        id="outcome-outside-testcase",
    ),
]

INVALID_REPORTS = [
    pytest.param(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='visible-pass'/><failure>hidden crash</failure>"
        "</testsuite>",
        "outcome elements outside testcase",
        id="direct-outcome-outside-testcase",
    ),
    pytest.param(
        "<testsuites tests='1' failures='0' errors='0' skipped='0'>"
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='visible-pass'/><wrapper><error>hidden crash</error></wrapper>"
        "</testsuite></testsuites>",
        "outcome elements outside testcase",
        id="wrapped-outcome-outside-testcase",
    ),
    pytest.param(
        "<testsuites tests='1' failures='0' errors='0' skipped='0'>"
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testsuite tests='1' failures='1' errors='0' skipped='0'>"
        "<testcase name='hidden'><failure/></testcase>"
        "</testsuite></testsuite></testsuites>",
        "failures",
        id="hidden-descendant-failure",
    ),
    pytest.param(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testsuites tests='1' failures='0' errors='1' skipped='0'>"
        "<testsuite tests='1' failures='0' errors='1' skipped='0'>"
        "<testcase name='hidden'><error/></testcase>"
        "</testsuite></testsuites></testsuite>",
        "errors",
        id="hidden-descendant-error",
    ),
    pytest.param(
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testsuite tests='1' failures='0' errors='0' skipped='1'>"
        "<testcase name='hidden'><skipped/></testcase></testsuite></testsuite>",
        "skipped",
        id="hidden-descendant-skip",
    ),
    pytest.param(
        "<testsuites tests='0' failures='0' errors='0' skipped='0'>"
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='hidden-pass'/></testsuite></testsuites>",
        "testsuites tests count 0",
        id="hidden-pass-under-zero-root-counter",
    ),
    pytest.param(
        "<testsuite tests='4' failures='0' errors='0' skipped='0'/>",
        "testcase subtree 0",
        id="fabricated-positive-counter",
    ),
    pytest.param(
        "<testsuites tests='1' failures='1' errors='0' skipped='0'>"
        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
        "<testcase name='pass'/></testsuite></testsuites>",
        "testsuites failures count 1",
        id="contradictory-wrapper-counter",
    ),
    pytest.param(
        "<testsuite tests='2' failures='0' errors='0' skipped='0'>"
        "<testcase name='only-one'/></testsuite>",
        "testsuite tests count 2",
        id="contradictory-suite-counter",
    ),
    pytest.param(
        "<testsuites><wrapper><testsuite tests='1'><testcase name='hidden-pass'/>"
        "</testsuite></wrapper></testsuites>",
        "malformed JUnit structure",
        id="malformed-wrapper",
    ),
    pytest.param(
        "<testsuites><testcase name='misplaced'/></testsuites>",
        "not a direct child",
        id="misplaced-testcase",
    ),
    pytest.param("<not-junit/>", "unexpected JUnit root", id="wrong-root"),
    pytest.param("<testsuite>", "malformed JUnit report", id="malformed-xml"),
    pytest.param(
        "<testsuites tests='0' failures='0' errors='0' skipped='0'/>",
        "zero executed tests",
        id="zero-tests",
    ),
    pytest.param(
        "<testsuite tests='1' failures='0' errors='0' skipped='1'>"
        "<testcase name='skip'><skipped/></testcase></testsuite>",
        "skipped",
        id="skipped-test",
    ),
]


def test_framework_report_accepts_valid_nested_report_via_api_and_ci_command(
    tmp_path: Path,
) -> None:
    report = _write(tmp_path, VALID_NESTED)
    expected = {"tests": 2, "failures": 0, "errors": 0, "skipped": 0}

    assert validate_junit_report(report) == expected
    json_report = tmp_path / "validation.json"
    completed = _ci_command(report, json_report)
    assert completed.returncode == 0
    assert json.loads(json_report.read_text(encoding="utf-8")) == {
        "schema": "osqar.framework-test-report.v1",
        "status": "PASS",
        **expected,
    }


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='pass'/></testsuite>",
            id="fully-unnamespaced",
        ),
        pytest.param(
            "<testsuites xmlns='urn:junit' tests='1' failures='0' errors='0' skipped='0'>"
            "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
            "<testcase name='pass'/></testsuite></testsuites>",
            id="consistently-namespaced",
        ),
    ],
)
def test_namespace_policy_accepts_consistent_controls(tmp_path: Path, body: str) -> None:
    report = _write(tmp_path, body)

    assert validate_junit_report(report) == {
        "tests": 1,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    assert _junit_rejection(report) is None
    assert _ci_command(report).returncode == 0


@pytest.mark.parametrize("body, message", JUNIT_CLOSED_GRAMMAR_REJECTIONS)
def test_closed_grammar_rejections_are_shared_by_api_helper_and_exact_cli(
    tmp_path: Path, body: str, message: str
) -> None:
    report = _write(tmp_path, body)

    with pytest.raises(FrameworkReportError, match=re.escape(message)):
        validate_junit_report(report)
    assert _junit_rejection(report) == message

    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")
    completed = _ci_command(report, json_report)

    assert completed.returncode == 2
    assert completed.stderr == f"ERROR: {message}\n"
    assert "Traceback" not in completed.stderr
    assert not json_report.exists()


@pytest.mark.parametrize("counter", INVALID_COUNTER_SPELLINGS)
def test_counter_grammar_rejects_noncanonical_values_via_api_and_exact_cli(
    tmp_path: Path, counter: str
) -> None:
    report = _write(
        tmp_path,
        f"<testsuite tests='{counter}' failures='0' errors='0' skipped='0'>"
        "<testcase name='pass'/></testsuite>",
    )
    with pytest.raises(FrameworkReportError, match="malformed testsuite tests count"):
        validate_junit_report(report)
    assert "malformed testsuite tests count" in (_junit_rejection(report) or "")

    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")
    completed = _ci_command(report, json_report)

    assert completed.returncode == 2
    assert "malformed testsuite tests count" in completed.stderr
    assert "Traceback" not in completed.stderr
    assert not json_report.exists()


def test_counter_grammar_accepts_canonical_zero_and_multi_digit_values(
    tmp_path: Path,
) -> None:
    cases = "".join(f"<testcase name='pass-{index}'/>" for index in range(10))
    report = _write(
        tmp_path,
        "<testsuite tests='10' failures='0' errors='0' skipped='0'>"
        f"{cases}</testsuite>",
    )

    assert validate_junit_report(report) == {
        "tests": 10,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    assert _ci_command(report).returncode == 0


def test_counter_grammar_enforces_bounded_64_bit_domain(tmp_path: Path) -> None:
    maximum = (1 << 63) - 1
    boundary = _write(
        tmp_path,
        f"<testsuite tests='{maximum}' failures='0' errors='0' skipped='0'>"
        "<testcase name='pass'/></testsuite>",
    )
    with pytest.raises(FrameworkReportError, match="does not match testcase subtree 1"):
        validate_junit_report(boundary)

    excessive = _write(
        tmp_path,
        f"<testsuite tests='{maximum + 1}' failures='0' errors='0' skipped='0'>"
        "<testcase name='pass'/></testsuite>",
    )
    with pytest.raises(FrameworkReportError, match=f"exceeds maximum {maximum}"):
        validate_junit_report(excessive)


def test_junit_nesting_accepts_boundary_and_rejects_next_level(
    tmp_path: Path,
) -> None:
    maximum_depth = 256
    boundary = _write(tmp_path, _nested_junit(maximum_depth))
    assert validate_junit_report(boundary)["tests"] == 1
    assert _ci_command(boundary).returncode == 0

    excessive = _write(tmp_path, _nested_junit(maximum_depth + 1))
    message = "JUnit structural nesting exceeds maximum depth 256"
    with pytest.raises(FrameworkReportError, match=message):
        validate_junit_report(excessive)
    assert _junit_rejection(excessive) == message


def test_exact_cli_rejects_deep_junit_without_traceback_or_stale_pass(
    tmp_path: Path,
) -> None:
    report = _write(tmp_path, _nested_junit(1100))
    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")

    completed = _ci_command(report, json_report)

    assert completed.returncode == 2
    assert (
        completed.stderr
        == "ERROR: JUnit structural nesting exceeds maximum depth 256\n"
    )
    assert "Traceback" not in completed.stderr
    assert not json_report.exists()


@pytest.mark.parametrize("body, message", INVALID_REPORTS)
def test_framework_report_rejects_each_invalid_class_via_api(
    tmp_path: Path, body: str, message: str
) -> None:
    with pytest.raises(FrameworkReportError, match=message):
        validate_junit_report(_write(tmp_path, body))


@pytest.mark.parametrize("body, message", INVALID_REPORTS)
def test_exact_ci_command_rejects_each_invalid_class_without_pass_json(
    tmp_path: Path, body: str, message: str
) -> None:
    report = _write(tmp_path, body)
    json_report = tmp_path / "validation.json"

    completed = _ci_command(report, json_report)

    assert completed.returncode == 2
    assert message in completed.stderr
    assert not json_report.exists()


def test_framework_report_rejects_missing_file_via_api_and_ci_command(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xml"
    with pytest.raises(FrameworkReportError, match="not found"):
        validate_junit_report(missing)
    assert _ci_command(missing).returncode == 2


@pytest.mark.parametrize("body, message", STALE_INVALID_REPORTS)
def test_cli_api_invalidates_stale_pass_json_for_each_invalid_input_class(
    tmp_path: Path, body: str | None, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "report.xml"
    if body is not None:
        report.write_text(body, encoding="utf-8")
    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")

    assert cli([str(report), "--json-report", str(json_report)]) == 2

    assert message in capsys.readouterr().err
    assert not json_report.exists()


@pytest.mark.parametrize("body, message", STALE_INVALID_REPORTS)
def test_exact_ci_command_invalidates_stale_pass_json_for_each_invalid_input_class(
    tmp_path: Path, body: str | None, message: str
) -> None:
    report = tmp_path / "report.xml"
    if body is not None:
        report.write_text(body, encoding="utf-8")
    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")

    completed = _ci_command(report, json_report)

    assert completed.returncode == 2
    assert message in completed.stderr
    assert not json_report.exists()


def test_cli_fails_before_validation_when_stale_output_cannot_be_unlinked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _write(tmp_path, VALID_NESTED)
    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")
    original_unlink = Path.unlink
    validation_called = False

    def fail_target_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path == json_report:
            raise PermissionError("unlink denied")
        original_unlink(path, *args, **kwargs)

    def record_validation(path: Path) -> dict[str, int]:
        nonlocal validation_called
        validation_called = True
        return validate_junit_report(path)

    monkeypatch.setattr(Path, "unlink", fail_target_unlink)
    monkeypatch.setattr(framework_test_report, "validate_junit_report", record_validation)

    assert cli([str(report), "--json-report", str(json_report)]) == 2

    assert capsys.readouterr().err == "ERROR: cannot invalidate JSON report: unlink denied\n"
    assert not validation_called
    assert json_report.read_text(encoding="utf-8") == STALE_PASS


def test_cli_removes_partial_temporary_output_when_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _write(tmp_path, VALID_NESTED)
    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")
    original_fdopen = framework_test_report.os.fdopen

    class FailingWriter:
        def __init__(self, fd: int) -> None:
            self.stream = original_fdopen(fd, "w", encoding="utf-8")

        def __enter__(self) -> FailingWriter:
            return self

        def write(self, _value: str) -> None:
            self.stream.write("{")
            self.stream.flush()
            raise OSError("write denied")

        def __exit__(self, *args: object) -> None:
            self.stream.close()

    monkeypatch.setattr(
        framework_test_report.os,
        "fdopen",
        lambda fd, *args, **kwargs: FailingWriter(fd),
    )

    assert cli([str(report), "--json-report", str(json_report)]) == 2

    assert capsys.readouterr().err == "ERROR: cannot write JSON report: write denied\n"
    assert not json_report.exists()
    assert not list(tmp_path.glob(".validation.json.*.tmp"))


def test_cli_removes_temporary_output_when_atomic_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _write(tmp_path, VALID_NESTED)
    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("replace denied")

    monkeypatch.setattr(framework_test_report.os, "replace", fail_replace)

    assert cli([str(report), "--json-report", str(json_report)]) == 2

    assert capsys.readouterr().err == "ERROR: cannot write JSON report: replace denied\n"
    assert not json_report.exists()
    assert not list(tmp_path.glob(".validation.json.*.tmp"))


def test_cli_fails_closed_when_json_serialization_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _write(tmp_path, VALID_NESTED)
    json_report = tmp_path / "validation.json"
    json_report.write_text(STALE_PASS, encoding="utf-8")

    def fail_serialization(*args: object, **kwargs: object) -> str:
        raise RuntimeError("serialization denied")

    monkeypatch.setattr(framework_test_report.json, "dumps", fail_serialization)

    assert cli([str(report), "--json-report", str(json_report)]) == 2

    assert capsys.readouterr().err == (
        "ERROR: cannot write JSON report: serialization denied\n"
    )
    assert not json_report.exists()
    assert not list(tmp_path.glob(".validation.json.*.tmp"))


def test_cli_invalidates_complete_pass_temp_when_replace_and_unlink_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = _write(tmp_path, VALID_NESTED)
    json_report = tmp_path / "validation.json"
    original_unlink = Path.unlink

    monkeypatch.setattr(
        framework_test_report.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace denied")),
    )

    def fail_temp_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path.name.startswith(".validation.json."):
            raise PermissionError("unlink denied")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_temp_unlink)

    assert cli([str(report), "--json-report", str(json_report)]) == 2
    assert capsys.readouterr().err == (
        "ERROR: cannot write JSON report: replace denied; "
        "temporary cleanup failed: unlink denied\n"
    )
    [temporary] = list(tmp_path.glob(".validation.json.*.tmp"))
    with pytest.raises(json.JSONDecodeError):
        json.loads(temporary.read_text(encoding="utf-8"))


@pytest.mark.parametrize("alias_kind", ["lexical", "symlink"])
def test_cli_rejects_junit_input_json_output_collision_before_invalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    alias_kind: str,
) -> None:
    report = _write(tmp_path, VALID_NESTED)
    before = report.read_bytes()
    json_report = report
    if alias_kind == "symlink":
        json_report = tmp_path / "validation.json"
        json_report.symlink_to(report)
    validation_called = False

    def record_validation(_path: Path) -> dict[str, int]:
        nonlocal validation_called
        validation_called = True
        return {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}

    monkeypatch.setattr(framework_test_report, "validate_junit_report", record_validation)

    assert cli([str(report), "--json-report", str(json_report)]) == 2
    assert capsys.readouterr().err == (
        "ERROR: JUnit input and JSON output resolve to the same path\n"
    )
    assert not validation_called
    assert report.read_bytes() == before
    if alias_kind == "symlink":
        assert json_report.is_symlink()
