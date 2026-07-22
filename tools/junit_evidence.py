"""Shared fail-closed grammar and accounting for JUnit XML evidence."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

COUNTERS = ("tests", "failures", "errors", "skipped")
OUTCOME_ELEMENTS = {"failure", "error", "skipped"}
STRUCTURAL_ELEMENTS = {"testsuite", "testsuites", "testcase"}
RECOGNIZED_ELEMENTS = STRUCTURAL_ELEMENTS | OUTCOME_ELEMENTS
MAX_STRUCTURAL_NESTING = 256
MAX_COUNTER_VALUE = (1 << 63) - 1
MAX_COUNTER_TEXT = str(MAX_COUNTER_VALUE)


class JUnitEvidenceError(ValueError):
    """Raised when JUnit structure or counters are not trustworthy."""


def _name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _namespace(element: ET.Element) -> str | None:
    if element.tag.startswith("{") and "}" in element.tag:
        return element.tag[1:].split("}", 1)[0]
    return None


def _namespace_label(namespace: str | None) -> str:
    return "<none>" if namespace is None else repr(namespace)


def _validate_namespaces(root: ET.Element) -> None:
    """Require every recognized JUnit element to use the root namespace."""
    expected = _namespace(root)
    for element in root.iter():
        element_name = _name(element)
        actual = _namespace(element)
        if element_name in RECOGNIZED_ELEMENTS and actual != expected:
            raise JUnitEvidenceError(
                "malformed JUnit namespace: recognized element "
                f"{element_name!r} uses namespace {_namespace_label(actual)}; "
                f"expected {_namespace_label(expected)}"
            )


def _declared(element: ET.Element, counter: str) -> int:
    raw = element.attrib.get(counter, "0")
    if re.fullmatch(r"(?:0|[1-9][0-9]*)", raw) is None:
        raise JUnitEvidenceError(
            f"invalid JUnit counters: malformed {_name(element)} {counter} count {raw!r}"
        )
    if len(raw) > len(MAX_COUNTER_TEXT) or (
        len(raw) == len(MAX_COUNTER_TEXT) and raw > MAX_COUNTER_TEXT
    ):
        raise JUnitEvidenceError(
            f"invalid JUnit counters: malformed {_name(element)} {counter} count "
            f"exceeds maximum {MAX_COUNTER_VALUE}"
        )
    return int(raw)


def _case_totals(case: ET.Element) -> dict[str, int]:
    descendants = list(case.iter())[1:]
    for element in descendants:
        element_name = _name(element)
        if element_name in STRUCTURAL_ELEMENTS:
            raise JUnitEvidenceError(
                f"malformed JUnit structure: testcase contains nested {element_name}"
            )

    direct_outcomes = [child for child in case if _name(child) in OUTCOME_ELEMENTS]
    all_outcomes = [
        element for element in descendants if _name(element) in OUTCOME_ELEMENTS
    ]
    if len(all_outcomes) != len(direct_outcomes):
        raise JUnitEvidenceError(
            "malformed JUnit structure: outcome elements must be direct children of testcase"
        )
    if len(direct_outcomes) > 1:
        raise JUnitEvidenceError(
            "malformed JUnit testcase outcomes: multiple outcome elements"
        )

    outcome_names = {_name(element) for element in direct_outcomes}
    return {
        "tests": 1,
        "failures": int("failure" in outcome_names),
        "errors": int("error" in outcome_names),
        "skipped": int("skipped" in outcome_names),
    }


def _add(target: dict[str, int], source: dict[str, int]) -> None:
    for counter in COUNTERS:
        target[counter] += source[counter]


def _validate_structural_depth(root: ET.Element) -> None:
    structural = {"testsuite", "testsuites"}
    root_depth = int(_name(root) in structural)
    pending = [(root, root_depth)]
    while pending:
        element, depth = pending.pop()
        for child in element:
            child_depth = depth + int(_name(child) in structural)
            if child_depth > MAX_STRUCTURAL_NESTING:
                raise JUnitEvidenceError(
                    "JUnit structural nesting exceeds maximum depth "
                    f"{MAX_STRUCTURAL_NESTING}"
                )
            pending.append((child, child_depth))


def _suite_totals(suite: ET.Element) -> dict[str, int]:
    totals = {counter: 0 for counter in COUNTERS}
    for child in suite:
        child_name = _name(child)
        if child_name == "testcase":
            _add(totals, _case_totals(child))
        elif child_name == "testsuite":
            _add(totals, _suite_totals(child))
        elif child_name == "testsuites":
            _add(totals, _container_totals(child))
        elif any(_name(descendant) in OUTCOME_ELEMENTS for descendant in child.iter()):
            raise JUnitEvidenceError(
                "malformed JUnit structure: outcome elements outside testcase"
            )
        elif any(_name(descendant) in {"testcase", "testsuite", "testsuites"} for descendant in child.iter()):
            raise JUnitEvidenceError(
                f"malformed JUnit structure: {_name(suite)} contains structural elements under {child_name!r}"
            )
    for counter in COUNTERS:
        declared = _declared(suite, counter)
        if declared != totals[counter]:
            raise JUnitEvidenceError(
                f"invalid JUnit counters: testsuite {counter} count {declared} does not match testcase subtree {totals[counter]}"
            )
    return totals


def _container_totals(container: ET.Element) -> dict[str, int]:
    totals = {counter: 0 for counter in COUNTERS}
    for child in container:
        child_name = _name(child)
        if child_name == "testsuite":
            _add(totals, _suite_totals(child))
        elif child_name == "testsuites":
            _add(totals, _container_totals(child))
        elif child_name == "testcase":
            raise JUnitEvidenceError(
                "malformed JUnit structure: testcase is not a direct child of testsuites"
            )
        elif any(_name(descendant) in OUTCOME_ELEMENTS for descendant in child.iter()):
            raise JUnitEvidenceError(
                "malformed JUnit structure: outcome elements outside testcase"
            )
        elif any(_name(descendant) in {"testcase", "testsuite", "testsuites"} for descendant in child.iter()):
            raise JUnitEvidenceError(
                f"malformed JUnit structure: testsuites contains structural elements under {child_name!r}"
            )
    for counter in COUNTERS:
        if counter in container.attrib:
            declared = _declared(container, counter)
            if declared != totals[counter]:
                raise JUnitEvidenceError(
                    f"invalid JUnit counters: testsuites {counter} count {declared} does not match descendant-suite total {totals[counter]}"
                )
    return totals


def validate_junit_tree(root: ET.Element) -> dict[str, int]:
    """Validate the complete JUnit tree and return testcase-derived totals."""
    root_name = _name(root)
    if root_name not in {"testsuite", "testsuites"}:
        raise JUnitEvidenceError(f"unexpected JUnit root element {root_name!r}")
    _validate_namespaces(root)
    _validate_structural_depth(root)
    if root_name == "testsuite":
        totals = _suite_totals(root)
    else:
        totals = _container_totals(root)

    all_cases = [element for element in root.iter() if _name(element) == "testcase"]
    complete = {counter: 0 for counter in COUNTERS}
    for case in all_cases:
        _add(complete, _case_totals(case))
    if complete != totals:
        raise JUnitEvidenceError(
            f"recognized JUnit totals {totals} do not match complete descendant testcase content {complete}"
        )
    if totals["tests"] == 0:
        raise JUnitEvidenceError("zero executed tests")
    return totals


def read_junit_report(path: Path) -> dict[str, int]:
    """Parse and validate a JUnit report from disk."""
    return validate_junit_tree(ET.parse(path).getroot())
